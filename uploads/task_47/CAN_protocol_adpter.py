"""
CAN/CANFD ISO-TP Protocol Adapter (with Byte Padding Support)

This module implements ISO 15765-2 (ISO-TP) protocol for data segmentation, 
reassembly, and flow control. Supports both standard CAN and CANFD modes with 
complete byte padding mechanism.

Byte Padding Rules:
- Data frames (Single/First/Consecutive): Pad to 8 bytes (CAN) or 64 bytes (CANFD) using 0xCC
- Flow control frames: Pad to 8 bytes using 0x00 or 0x55
- Receiving: Automatically removes padding based on length info in PCI
"""
from typing import List, Optional, Tuple
from enum import IntEnum
import logging
from datetime import datetime


class FrameType(IntEnum):
    """ISO-TP frame type definitions"""
    SINGLE = 0          # Single frame
    FIRST = 1           # First frame
    CONSECUTIVE = 2     # Consecutive frame
    FLOW_CONTROL = 3    # Flow control frame


class FlowStatus(IntEnum):
    """Flow control status definitions"""
    CTS = 0         # Continue To Send
    WAIT = 1        # Wait
    OVERFLOW = 2    # Overflow - buffer overflow


# ==================== Custom Exceptions ====================
class ProtocolError(Exception):
    """Base protocol error class"""
    pass


class FrameLengthError(ProtocolError):
    """Frame length error"""
    pass


class SequenceError(ProtocolError):
    """Sequence number error"""
    pass


class FlowControlError(ProtocolError):
    """Flow control error"""
    pass


# ==================== Protocol Adapter Main Class ====================
class CAN_Protocol_Adapter:
    """
    CAN/CANFD ISO-TP Protocol Adapter
    
    Main Features:
    - Data segmentation and reassembly
    - Flow control management
    - Sequence number management
    - Byte padding and unpadding
    - Error detection and exception handling
    """
    
    # Padding byte definitions
    DATA_PADDING_BYTE = 0xAA    # Data frame padding byte (ISO-TP standard recommendation)
    FC_PADDING_BYTE = 0x00      # Flow control frame padding byte (0x55 can also be used)
    CAN_FD_DLC = [0, 1, 2, 3, 4, 5, 6, 7, 8, 12, 16, 20, 24, 32, 48, 64]
    
    def __init__(self, 
                 is_canfd: bool = False, 
                 padding_enabled: bool = True,
                 logger: Optional[logging.Logger] = None) -> None:
        """
        Initialize protocol adapter
        
        Args:
            is_canfd (bool): True for CANFD protocol (64 bytes), False for CAN protocol (8 bytes)
            padding_enabled (bool): Whether to enable byte padding
            logger (Optional[logging.Logger]): Logger instance, creates default logger if None
            
        Returns:
            None
        """
        self.is_canfd = is_canfd
        self.padding_enabled = padding_enabled
        self.logger = logger or self._create_default_logger()
        
        # Initialize protocol parameters
        self._init_proto_params()
        
        # Initialize receive state
        self.reset()
        
        # Initialize flow control parameters (used by receiver)
        self.block_size = 0   # 0=unlimited, >0=max consecutive frames per block
        self.st_min = 0       # Minimum time interval between consecutive frames (ms)
        
        # Initialize send state
        self._reset_send_state()
        
        self.logger.info(
            f"Protocol adapter initialized: "
            f"{'CANFD' if is_canfd else 'CAN'}, "
            f"max_frame_size={self.max_frame_size}, "
            f"single_frame_max_data={self.single_frame_data_max_length}, "
            f"padding={'enabled' if padding_enabled else 'disabled'}"
        )
    
    def _create_default_logger(self) -> logging.Logger:
        """
        Create default logger
        
        Returns:
            logging.Logger: Configured logger instance
        """
        logger = logging.getLogger(
            f"CAN_Protocol_{'CANFD' if self.is_canfd else 'CAN'}"
        )
        logger.setLevel(logging.INFO)
        
        # Add console handler if no handlers exist
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _init_proto_params(self) -> None:
        """
        Initialize protocol parameters
        
        CAN Protocol:
            - Max frame length: 8 bytes
            - Single frame max data: 7 bytes (1 byte PCI + 7 bytes data)
            
        CANFD Protocol:
            - Max frame length: 64 bytes
            - Single frame max data: 62 bytes (2 bytes PCI + 62 bytes data)
            
        Returns:
            None
        """
        if not self.is_canfd:
            self.max_frame_size = 8
            self.single_frame_data_max_length = 7  # 1 byte PCI
        else:
            self.max_frame_size = 64
            self.single_frame_data_max_length = 62  # 2 bytes PCI
    
    def _pad_frame(self, frame_data: bytes, is_flow_control: bool = False, is_consecutive_frame: bool = False) -> bytes:
        """
        Byte padding: pad frame to fixed length
        
        Args:
            frame_data (bytes): Original frame data
            is_flow_control (bool): Whether this is a flow control frame
            
        Returns:
            bytes: Padded frame data
        """
        if not self.padding_enabled:
            return frame_data
        
        current_len = len(frame_data)
        
        if current_len >= self.max_frame_size:
            return frame_data
        
        padding_size = 0
        standard_CAN_size = 8
        Extended_CAN_size = 64
        
        if current_len <= 8:
            if is_consecutive_frame:
                padding_size = Extended_CAN_size - current_len
            else:
                padding_size = standard_CAN_size - current_len
            
        else:
            for dlc, nof_bytes in enumerate(self.CAN_FD_DLC):
                if nof_bytes >= current_len:
                    # Calculate required padding bytes
                    padding_size = nof_bytes - current_len
                    break
        
        # Select padding byte
        padding_byte = self.FC_PADDING_BYTE if is_flow_control else self.DATA_PADDING_BYTE
        
        # Apply padding
        padded_frame = frame_data + bytes([padding_byte] * padding_size)
        
        self.logger.info(
            f"Padding: {current_len} bytes -> {len(padded_frame)} bytes, "
            f"pad_value=0x{padding_byte:02X}, "
            f"type={'flow_control' if is_flow_control else 'data'}"
        )
        
        return padded_frame
    
    def _unpad_frame(self, frame_data: bytes, actual_length: int) -> bytes:
        """
        Remove padding bytes: extract valid data based on actual data length
        
        Args:
            frame_data (bytes): Frame data with padding
            actual_length (int): Actual valid data length
            
        Returns:
            bytes: Data with padding removed
        """
        if actual_length > len(frame_data):
            self.logger.warning(
                f"Actual length ({actual_length}) exceeds frame length ({len(frame_data)}), "
                f"using frame length"
            )
            return frame_data
        
        return frame_data[:actual_length]
    
    # ==================== Send Related Methods ====================
    
    def send(self, data: bytes) -> List[bytes]:
        """
        Send data, automatically choose single-frame or multi-frame transmission
        
        Args:
            data (bytes): Data to send
            
        Returns:
            List[bytes]: Frame list. Returns 1 frame for single-frame transmission;
                        for multi-frame, only returns first frame. Call 
                        send_consecutive_frames() to get subsequent frames
            
        Raises:
            ValueError: If data is empty or too long
        """
        if not data:
            raise ValueError("Send data cannot be empty")
        
        if len(data) > 4095:  # ISO-TP max support is 4095 bytes
            raise ValueError(f"Data length exceeds limit: {len(data)} > 4095")
        
        self._reset_send_state()
        
        # Log: record original send data
        self.logger.info("=" * 60)
        self.logger.info(f"[SEND] Original data: {data.hex().upper()} ({len(data)} bytes)")
        
        if len(data) <= self.single_frame_data_max_length:
            # Single frame transmission
            frame = self._create_single_frame(data)
            pci_len = 1 if not self.is_canfd else 2
            padding_len = len(frame) - len(data) - pci_len
            
            self.logger.info(f"[SEND] Frame type: Single Frame")
            self.logger.info(f"[SEND] Data length: {len(data)} bytes")
            self.logger.info(f"[SEND] Frame content: {frame.hex().upper()}")
            self.logger.info(
                f"[SEND] Frame length: {len(frame)} bytes "
                f"(PCI={pci_len} + data={len(data)} + padding={padding_len})"
            )
            self.logger.info("=" * 60)
            return [frame]
        else:
            # Multi-frame transmission - create first frame only
            first_frame = self._create_first_frame(data)
            
            # Save pending data state
            self.pending_data = data
            # Calculate actual data carried by first frame (excluding PCI and padding)
            self.sent_data_length = min(
                len(data),
                self.max_frame_size - 2  # 2 bytes PCI
            )
            self.next_sequence = 1
            
            padding_len = len(first_frame) - 2 - self.sent_data_length
            
            self.logger.info(f"[SEND] Frame type: First Frame")
            self.logger.info(f"[SEND] Total data length: {len(data)} bytes")
            self.logger.info(f"[SEND] First frame data: {self.sent_data_length} bytes")
            self.logger.info(f"[SEND] Frame content: {first_frame.hex().upper()}")
            self.logger.info(
                f"[SEND] Frame length: {len(first_frame)} bytes "
                f"(PCI=2 + data={self.sent_data_length} + padding={padding_len})"
            )
            self.logger.info("=" * 60)
            return [first_frame]
    
    def send_consecutive_frames(self, max_frames: Optional[int] = None) -> List[bytes]:
        """
        Send consecutive frames
        
        Args:
            max_frames (Optional[int]): Maximum number of consecutive frames to send 
                                       (based on BlockSize from flow control frame).
                                       None means send all remaining data
            
        Returns:
            List[bytes]: List of consecutive frames
            
        Raises:
            RuntimeError: No pending data (send() not called or transmission complete)
        """
        if not hasattr(self, 'pending_data') or self.pending_data is None:
            raise RuntimeError("No pending data, please call send() method first")
        
        frames = []
        remaining_data = self.pending_data[self.sent_data_length:]
        frame_count = 0
        
        self.logger.info(
            f"Start sending consecutive frames: remaining={len(remaining_data)} bytes, "
            f"max_frames={max_frames or 'unlimited'}"
        )
        
        while remaining_data and (max_frames is None or frame_count < max_frames):
            # Build PCI: upper 4 bits=2(consecutive), lower 4 bits=sequence number (0-15 cycle)
            pci = (FrameType.CONSECUTIVE.value << 4) | (self.next_sequence & 0x0F)
            
            # Calculate data payload size for this frame (1 byte PCI + data)
            payload_size = min(len(remaining_data), self.max_frame_size - 1)
            
            # Build frame data: PCI(1 byte) + data
            frame_data = bytes([pci]) + remaining_data[:payload_size]
            
            # Byte padding
            padded_frame = self._pad_frame(frame_data, is_flow_control=False, is_consecutive_frame=True)
            frames.append(padded_frame)
            
            self.logger.info(
                f"Consecutive frame SN={self.next_sequence}: "
                f"valid_data={len(frame_data)} bytes, "
                f"padded={len(padded_frame)} bytes"
            )
            self.logger.info(f"Frame content: {padded_frame.hex().upper()}")
            
            # Update state
            self.sent_data_length += payload_size
            remaining_data = remaining_data[payload_size:]
            self.next_sequence = (self.next_sequence + 1) % 16
            frame_count += 1
        
        # Clear state if transmission complete
        if not remaining_data:
            self.logger.info(f"Multi-frame transmission complete: sent {self.sent_data_length} bytes")
            self.pending_data = None
        
        return frames
    
    def _create_single_frame(self, data: bytes) -> bytes:
        """
        Create single frame
        
        Frame format:
            CAN:   [PCI(1B)] [Data(0-7B)] [Padding]
            CANFD: [PCI(2B)] [Data(0-62B)] [Padding]
        
        Args:
            data (bytes): Data to send
            
        Returns:
            bytes: Complete single frame data (with padding)
        """
        data_len = len(data)
        
        if self.is_canfd:
            # CANFD uses 2-byte PCI
            pci_bytes = self._encode_pci_length(data_len, FrameType.SINGLE)
        else:
            # CAN uses 1-byte PCI
            pci_bytes = bytes([(FrameType.SINGLE.value << 4) | data_len])
        
        # Build frame: PCI + data
        frame = pci_bytes + data
        
        # Byte padding
        padded_frame = self._pad_frame(frame, is_flow_control=False)
        
        return padded_frame
    
    def _create_first_frame(self, data: bytes) -> bytes:
        """
        Create first frame
        
        Frame format:
            [PCI(2B)] [Data(...)] [Padding]
            PCI byte 1: upper 4 bits=1(first frame), lower 4 bits=upper 4 bits of total length
            PCI byte 2: lower 8 bits of total length
        
        Args:
            data (bytes): Complete data to send
            
        Returns:
            bytes: First frame data (with padding)
        """
        total_len = len(data)
        pci_bytes = self._encode_pci_length(total_len, FrameType.FIRST)
        
        # Calculate data payload size for first frame
        payload_size = self.max_frame_size - len(pci_bytes)
        
        # Build frame: PCI + data
        frame = pci_bytes + data[:payload_size]
        
        # Byte padding
        padded_frame = self._pad_frame(frame, is_flow_control=False)
        
        return padded_frame
    
    def create_flow_control_frame(self, 
                                  flow_status: int = FlowStatus.CTS.value,
                                  block_size: int = 0, 
                                  st_min: int = 0) -> bytes:
        """
        Create flow control frame
        
        Frame format:
            [PCI(1B)] [BS(1B)] [STmin(1B)] [Padding]
            
        Args:
            flow_status (int): Flow status 
                              0=CTS(continue to send), 1=Wait, 2=Overflow
            block_size (int): Block size
                             0=unlimited consecutive frames
                             1-255=number of consecutive frames before next flow control
            st_min (int): Minimum time interval between consecutive frames
                         0x00-0x7F: 0-127ms
                         0xF1-0xF9: 100-900μs
                   
        Returns:
            bytes: Flow control frame data (with padding)
            
        Raises:
            ValueError: Invalid parameter values
        """
        if flow_status not in [0, 1, 2]:
            raise ValueError(f"Invalid flow status: {flow_status}")
        
        if not (0 <= block_size <= 255):
            raise ValueError(f"Invalid block size: {block_size}")
        
        if not (0 <= st_min <= 255):
            raise ValueError(f"Invalid STmin: {st_min}")
        
        pci = (FrameType.FLOW_CONTROL.value << 4) | (flow_status & 0x0F)
        frame = bytes([pci, block_size & 0xFF, st_min & 0xFF])
        
        # Flow control frame uses special padding byte
        padded_frame = self._pad_frame(frame, is_flow_control=True)
        
        self.logger.info(
            f"Create flow control frame: FS={flow_status}, BS={block_size}, "
            f"STmin={st_min}, length={len(padded_frame)} bytes"
        )
        
        return padded_frame
    
    def _encode_pci_length(self, length: int, frame_type: FrameType) -> bytes:
        """
        Encode PCI bytes (including length information)
        
        Args:
            length (int): Data length
            frame_type (FrameType): Frame type
            
        Returns:
            bytes: PCI byte sequence (1 or 2 bytes)
        """
        # Use 12 bits to represent length (max 4095)
        pci_high = (frame_type.value << 4) | ((length >> 8) & 0x0F)
        pci_low = length & 0xFF
        return bytes([pci_high, pci_low])
    
    def _reset_send_state(self) -> None:
        """
        Reset send state
        
        Returns:
            None
        """
        self.pending_data = None
        self.sent_data_length = 0
        self.next_sequence = 0
    
    # ==================== Receive Related Methods ====================
    
    def reset(self) -> None:
        """
        Reset receiver state
        
        Returns:
            None
        """
        self.receiving = False
        self.expected_sequence = 0
        self.total_length = 0
        self.received_data = bytearray()
        self.logger.info("Receiver state reset")
    
    def receive(self, frame_data: bytes) -> Tuple[Optional[bytes], Optional[bytes]]:
        """
        Receive and parse frame data
        
        Args:
            frame_data (bytes): Received CAN frame data (may include padding bytes)
            
        Returns:
            Tuple[Optional[bytes], Optional[bytes]]: (complete_data, flow_control_frame)
                - complete_data: Returned when single/multi-frame reception complete, None otherwise
                - flow_control_frame: Returned when first frame received, None otherwise
            
        Raises:
            FrameLengthError: Invalid frame length
            SequenceError: Sequence number error
            ProtocolError: Other protocol errors
        """
        if not frame_data:
            raise FrameLengthError("Received empty frame")
        
        if len(frame_data) > self.max_frame_size:
            raise FrameLengthError(
                f"Frame length exceeds limit: {len(frame_data)} > {self.max_frame_size}"
            )
        
        pci_byte = frame_data[0]
        frame_type = (pci_byte >> 4) & 0x0F
        
        self.logger.info(
            f"Receive frame: type={frame_type}, length={len(frame_data)} bytes, "
            f"content={frame_data.hex().upper()}"
        )
        
        try:
            if frame_type == FrameType.SINGLE.value:
                data = self._parse_single_frame(frame_data)
                return (data, None)
            
            elif frame_type == FrameType.FIRST.value:
                self._parse_first_frame(frame_data)
                # After receiving first frame, generate and return flow control frame
                fc_frame = self.create_flow_control_frame(
                    flow_status=FlowStatus.CTS.value,
                    block_size=self.block_size,
                    st_min=self.st_min
                )
                self.logger.info(
                    f"Received first frame, send flow control: BS={self.block_size}, "
                    f"STmin={self.st_min}ms"
                )
                self.logger.info(f"Flow control content: {fc_frame.hex().upper()}")
                return (None, fc_frame)
            
            elif frame_type == FrameType.CONSECUTIVE.value:
                data = self._parse_consecutive_frame(frame_data)
                
                # If block_size is set, send flow control again after receiving specified number of frames
                fc_frame = None
                if data is None and self.block_size > 0:
                    # Check if need to send new flow control frame
                    frames_received = (self.expected_sequence - 1) % 16
                    if frames_received > 0 and frames_received % self.block_size == 0:
                        fc_frame = self.create_flow_control_frame(
                            FlowStatus.CTS.value, 
                            self.block_size, 
                            self.st_min
                        )
                        self.logger.info(
                            f"Send intermediate flow control: received {frames_received} frames"
                        )
                
                return (data, fc_frame)
            
            elif frame_type == FrameType.FLOW_CONTROL.value:
                self._parse_flow_control_frame(frame_data)
                return (None, None)
            
            else:
                raise ProtocolError(f"Unknown frame type: {frame_type}")
                
        except Exception as e:
            self.logger.error(f"Frame parsing error: {e}")
            raise
    
    def _parse_single_frame(self, frame_data: bytes) -> bytes:
        """
        Parse single frame (automatically remove padding bytes)
        
        Args:
            frame_data (bytes): Single frame data (may include padding)
            
        Returns:
            bytes: Extracted data portion (without padding)
            
        Raises:
            FrameLengthError: Frame length mismatch
        """
        pci_byte = frame_data[0]
        
        if self.is_canfd:
            # CANFD uses 2-byte PCI
            if len(frame_data) < 2:
                raise FrameLengthError("CANFD single frame length less than 2 bytes")
            
            data_len = ((pci_byte & 0x0F) << 8) | frame_data[1]
            data_start = 2
        else:
            # CAN uses 1-byte PCI
            data_len = pci_byte & 0x0F
            data_start = 1
        
        # Calculate expected frame length (PCI + data)
        expected_frame_len = data_start + data_len
        
        if len(frame_data) < expected_frame_len:
            raise FrameLengthError(
                f"Single frame data length insufficient: expected at least {expected_frame_len} bytes, "
                f"actual {len(frame_data)} bytes"
            )
        
        # Remove padding, extract valid data only
        data = self._unpad_frame(
            frame_data[data_start:],
            data_len
        )
        
        self.logger.info(
            f"Parse single frame: data_length={data_len} bytes, "
            f"frame_length={len(frame_data)} bytes"
        )
        
        return data
    
    def _parse_first_frame(self, frame_data: bytes) -> None:
        """
        Parse first frame (automatically remove padding bytes)
        
        Args:
            frame_data (bytes): First frame data (may include padding)
            
        Returns:
            None
            
        Raises:
            FrameLengthError: Invalid frame length
        """
        if len(frame_data) < 3:
            raise FrameLengthError("First frame length less than 3 bytes")
        
        # Reset receive state
        self.reset()
        self.receiving = True
        
        # Parse total length (12 bits)
        self.total_length = ((frame_data[0] & 0x0F) << 8) | frame_data[1]
        
        # Extract first frame data portion (remove padding)
        data_start = 2
        
        # Calculate actual data carried by first frame
        first_frame_data_len = min(
            self.total_length,
            self.max_frame_size - 2  # Subtract PCI length
        )
        
        # Remove padding bytes
        self.received_data = bytearray(
            self._unpad_frame(
                frame_data[data_start:],
                first_frame_data_len
            )
        )
        
        self.expected_sequence = 1
        
        self.logger.info(
            f"Parse first frame: total_length={self.total_length} bytes, "
            f"first_frame_data={len(self.received_data)} bytes, "
            f"frame_length={len(frame_data)} bytes"
        )
    
    def _parse_consecutive_frame(self, frame_data: bytes) -> Optional[bytes]:
        """
        Parse consecutive frame (automatically remove padding bytes)
        
        Args:
            frame_data (bytes): Consecutive frame data (may include padding)
            
        Returns:
            Optional[bytes]: Returns complete data if reception complete, None otherwise
            
        Raises:
            SequenceError: Sequence number error
            ProtocolError: Not in receiving state
        """
        if not self.receiving:
            raise ProtocolError("Not in receiving state, cannot receive consecutive frame")
        
        # Extract sequence number
        sequence = frame_data[0] & 0x0F
        
        # Verify sequence number
        if sequence != self.expected_sequence:
            self.reset()
            raise SequenceError(
                f"Sequence number error: expected {self.expected_sequence}, actual {sequence}"
            )
        
        # Calculate data payload size for this frame
        remaining_data = self.total_length - len(self.received_data)
        payload_size = min(remaining_data, self.max_frame_size - 1)
        
        # Extract data and remove padding
        payload = self._unpad_frame(frame_data[1:], payload_size)
        self.received_data.extend(payload)
        
        self.logger.info(
            f"Consecutive frame SN={sequence}: valid_data={len(payload)} bytes, "
            f"accumulated={len(self.received_data)}/{self.total_length} bytes"
        )
        
        # Update sequence number
        self.expected_sequence = (self.expected_sequence + 1) % 16
        
        # Check if reception complete
        if len(self.received_data) >= self.total_length:
            data = bytes(self.received_data[:self.total_length])
            self.logger.info(f"Multi-frame reception complete: total_length={len(data)} bytes")
            self.reset()
            return data
        
        return None
    
    def _parse_flow_control_frame(self, frame_data: bytes) -> None:
        """
        Parse flow control frame
        
        Note: Flow control frame has fixed 3 bytes valid data, rest are padding bytes
        
        Args:
            frame_data (bytes): Flow control frame data (may include padding)
            
        Returns:
            None
            
        Raises:
            FrameLengthError: Insufficient frame length
            FlowControlError: Flow status is OVERFLOW
        """
        if len(frame_data) < 3:
            raise FrameLengthError("Flow control frame length less than 3 bytes")
        
        # Flow control frame has fixed 3 bytes valid data, extract first 3 bytes
        pci_byte    = frame_data[0]
        flow_status = pci_byte & 0x0F
        block_size  = frame_data[1]
        st_min      = frame_data[2]
        
        # Save flow control parameters (used by sender)
        self.flow_status = flow_status
        self.block_size = block_size
        self.st_min = st_min
        
        status_name = {
            0: 'CTS', 
            1: 'WAIT', 
            2: 'OVERFLOW'
        }.get(flow_status, 'UNKNOWN')
        
        self.logger.info(
            f"Parse flow control frame: FS={status_name}, BS={block_size}, "
            f"STmin={st_min}ms"
        )
        
        if flow_status == FlowStatus.OVERFLOW.value:
            raise FlowControlError("Receiver buffer overflow")