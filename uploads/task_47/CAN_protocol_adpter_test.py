"""
CAN Protocol Adapter Integration Test Suite

Comprehensive integration tests for CAN/CANFD ISO-TP protocol adapter.
Tests cover single-frame, multi-frame transmissions, flow control, error handling,
and edge cases.
"""
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime
from typing import Callable, List

from proto.CAN_protocol_adpter import (
    CAN_Protocol_Adapter,
    FrameType,
    FlowStatus,
    ProtocolError,
    FrameLengthError,
    SequenceError,
    FlowControlError
)


class TestLogger:
    """
    Test logger manager for integration tests
    
    Manages logging configuration for test execution with both file and console output.
    """
    
    def __init__(self, log_file: str = None):
        """
        Initialize test logger
        
        Args:
            log_file (str, optional): Custom log file path. If None, creates timestamped file
        """
        if log_file is None:
            # Create logs directory if not exists
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            
            # Create log filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.log_file = log_dir / f"can_protocol_integration_test_{timestamp}.log"
        else:
            self.log_file = Path(log_file)
        
        self.setup_logging()
    
    def setup_logging(self) -> None:
        """
        Configure logging system with file and console handlers
        
        Returns:
            None
        """
        # Clear old log handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Configure log format
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        date_format = '%Y-%m-%d %H:%M:%S'
        
        # File handler with rotation
        file_handler = RotatingFileHandler(
            self.log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8',
            mode='w'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(log_format, date_format))
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter(log_format, date_format))
        
        # Configure root logger
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
        logging.info(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logging.info(f"Log file: {self.log_file}")
        logging.info("=" * 80)


def test_single_frame_can():
    """
    Test CAN single frame transmission
    
    Verifies:
    - Single frame creation and transmission
    - Data integrity after reception
    - No flow control frame generation
    """
    logging.info("[Test 1] CAN Single Frame Transmission")
    
    tx = CAN_Protocol_Adapter(is_canfd=False)
    rx = CAN_Protocol_Adapter(is_canfd=False)
    
    # Test short data
    test_data = bytes([0x10, 0x01, 0x02])
    frames = tx.send(test_data)
    
    assert len(frames) == 1, "Single frame transmission should return 1 frame"
    
    data, fc = rx.receive(frames[0])
    
    assert fc is None, "Single frame should not generate flow control"
    assert data == test_data, f"Data mismatch: {data.hex()} != {test_data.hex()}"
    
    logging.info("✓ CAN single frame transmission test passed\n")


def test_single_frame_canfd():
    """
    Test CANFD single frame transmission
    
    Verifies:
    - CANFD single frame with larger payload
    - Data integrity for 50-byte payload
    """
    logging.info("[Test 2] CANFD Single Frame Transmission")
    
    tx = CAN_Protocol_Adapter(is_canfd=True)
    rx = CAN_Protocol_Adapter(is_canfd=True)
    
    # Test longer data (but still within single frame range)
    test_data = bytes(range(1, 51))  # 50 bytes
    frames = tx.send(test_data)
    
    assert len(frames) == 1, "Single frame transmission should return 1 frame"
    
    data, fc = rx.receive(frames[0])
    
    assert fc is None, "Single frame should not generate flow control"
    assert data == test_data, "Data mismatch"
    
    logging.info("✓ CANFD single frame transmission test passed\n")


def test_multi_frame_without_flow_control():
    """
    Test multi-frame transmission without block size limit
    
    Verifies:
    - First frame and flow control generation
    - Consecutive frames transmission
    - Complete data reception
    """
    logging.info("[Test 3] Multi-frame Transmission (No Flow Control Limit)")
    
    tx = CAN_Protocol_Adapter(is_canfd=True)
    rx = CAN_Protocol_Adapter(is_canfd=True)
    
    # Set receiver flow control parameters: no block size limit
    rx.block_size = 0
    rx.st_min = 0
    
    # Create test data (100 bytes)
    test_data = bytes(range(1, 101))
    
    # Send first frame
    frames = tx.send(test_data)
    data, fc_frame = rx.receive(frames[0])
    
    assert data is None, "First frame should not return complete data"
    assert fc_frame is not None, "First frame should generate flow control"
    
    # Sender processes flow control frame
    tx.receive(fc_frame)
    
    # Send all consecutive frames
    consecutive_frames = tx.send_consecutive_frames()
    
    for cf in consecutive_frames:
        data, fc = rx.receive(cf)
        if data:
            break
    
    assert data == test_data, "Received data does not match sent data"
    logging.info("✓ Multi-frame transmission (no flow control limit) test passed\n")


def test_multi_frame_with_block_size():
    """
    Test multi-frame transmission with block size limit
    
    Verifies:
    - Block-based transmission with flow control
    - Multiple flow control frame handling
    - Large data (600 bytes) integrity
    """
    logging.info("[Test 4] Multi-frame Transmission (Block Size Limit)")
    
    tx = CAN_Protocol_Adapter(is_canfd=True)
    rx = CAN_Protocol_Adapter(is_canfd=True)
    
    # Set receiver flow control parameters: 5 frames per block
    rx.block_size = 5
    rx.st_min = 10
    
    # Create test data (600 bytes, requires multiple blocks)
    test_data = bytes([(i % 256) for i in range(1, 601)])
    
    # Send first frame
    frames = tx.send(test_data)
    data, fc_frame = rx.receive(frames[0])
    
    assert fc_frame is not None, "First frame should generate flow control"
    
    # Sender processes flow control frame
    tx.receive(fc_frame)
    
    # Send consecutive frames in blocks
    block_count = 0
    while True:
        max_frames = tx.block_size if tx.block_size > 0 else None
        consecutive_frames = tx.send_consecutive_frames(max_frames)
        
        if not consecutive_frames:
            break
        
        block_count += 1
        logging.info(f"Sending block {block_count}: {len(consecutive_frames)} frames")
        
        for cf in consecutive_frames:
            data, fc_frame = rx.receive(cf)
            
            if data:
                # Reception complete
                assert data == test_data, "Received data does not match sent data"
                logging.info("✓ Multi-frame transmission (block size limit) test passed\n")
                return
            
            # Handle intermediate flow control frame
            if fc_frame:
                logging.info("Received intermediate flow control, continue sending next block")
                tx.receive(fc_frame)
                break


def test_sequence_error():
    """
    Test sequence number error handling
    
    Verifies:
    - Correct sequence number validation
    - SequenceError exception on out-of-order frames
    """
    logging.info("[Test 5] Sequence Number Error Handling")
    
    tx = CAN_Protocol_Adapter(is_canfd=False)
    rx = CAN_Protocol_Adapter(is_canfd=False)
    
    # Create data requiring multiple frames
    test_data = bytes(range(1, 30))
    
    # Send first frame
    frames = tx.send(test_data)
    data, fc_frame = rx.receive(frames[0])
    tx.receive(fc_frame)
    
    # Get consecutive frames
    consecutive_frames = tx.send_consecutive_frames()
    
    # Normally receive first frame
    rx.receive(consecutive_frames[0])
    
    # Skip a frame to create sequence error
    try:
        rx.receive(consecutive_frames[2])  # Expected SN=2, actual SN=3
        assert False, "Should raise sequence number error"
    except SequenceError as e:
        logging.info(f"✓ Correctly caught sequence error: {e}\n")


def test_frame_length_error():
    """
    Test frame length error handling
    
    Verifies:
    - Empty frame rejection
    - Oversized frame rejection
    """
    logging.info("[Test 6] Frame Length Error Handling")
    
    rx = CAN_Protocol_Adapter(is_canfd=False)
    
    # Test empty frame
    try:
        rx.receive(bytes())
        assert False, "Should raise frame length error"
    except FrameLengthError as e:
        logging.info(f"✓ Correctly caught empty frame error: {e}")
    
    # Test oversized frame
    try:
        rx.receive(bytes(100))
        assert False, "Should raise frame length error"
    except FrameLengthError as e:
        logging.info(f"✓ Correctly caught oversized frame error: {e}\n")


def test_overflow_flow_control():
    """
    Test overflow flow control handling
    
    Verifies:
    - Overflow status in flow control frame
    - FlowControlError exception on overflow
    """
    logging.info("[Test 7] Overflow Flow Control Handling")
    
    tx = CAN_Protocol_Adapter(is_canfd=False)
    rx = CAN_Protocol_Adapter(is_canfd=False)
    
    # Create overflow flow control frame
    overflow_fc = rx.create_flow_control_frame(
        flow_status=FlowStatus.OVERFLOW.value,
        block_size=0,
        st_min=0
    )
    
    # Sender receives overflow flow control
    try:
        tx.receive(overflow_fc)
        assert False, "Should raise flow control error"
    except FlowControlError as e:
        logging.info(f"✓ Correctly caught overflow error: {e}\n")


def test_edge_cases():
    """
    Test edge cases and boundary conditions
    
    Verifies:
    - Maximum single frame data for CAN (7 bytes)
    - Minimum multi-frame data for CAN (8 bytes)
    - Maximum single frame data for CANFD (62 bytes)
    - Maximum data length (4095 bytes)
    """
    logging.info("[Test 8] Edge Cases Testing")
    
    # Test maximum single frame data (CAN)
    tx_can = CAN_Protocol_Adapter(is_canfd=False)
    rx_can = CAN_Protocol_Adapter(is_canfd=False)
    max_single_data_can = bytes(range(7))
    
    frames = tx_can.send(max_single_data_can)
    assert len(frames) == 1, "Should use single frame transmission"
    data, _ = rx_can.receive(frames[0])
    assert data == max_single_data_can
    logging.info("✓ CAN maximum single frame data test passed")
    
    # Test minimum multi-frame data (CAN)
    min_multi_data_can = bytes(range(8))
    frames = tx_can.send(min_multi_data_can)
    assert len(frames) == 1, "Should return first frame"
    data, fc = rx_can.receive(frames[0])
    assert fc is not None, "Should generate flow control"
    logging.info("✓ CAN minimum multi-frame data test passed")
    
    # Test maximum single frame data (CANFD)
    tx_fd = CAN_Protocol_Adapter(is_canfd=True)
    rx_fd = CAN_Protocol_Adapter(is_canfd=True)
    max_single_data_fd = bytes(range(62))
    
    frames = tx_fd.send(max_single_data_fd)
    assert len(frames) == 1, "Should use single frame transmission"
    data, _ = rx_fd.receive(frames[0])
    assert data == max_single_data_fd
    logging.info("✓ CANFD maximum single frame data test passed")
    
    # Test maximum length data (4095 bytes)
    tx_max = CAN_Protocol_Adapter(is_canfd=True)
    rx_max = CAN_Protocol_Adapter(is_canfd=True)
    rx_max.block_size = 0
    
    max_data = bytes([(i % 256) for i in range(4095)])
    frames = tx_max.send(max_data)
    data, fc = rx_max.receive(frames[0])
    tx_max.receive(fc)
    
    consecutive_frames = tx_max.send_consecutive_frames()
    for cf in consecutive_frames:
        data, _ = rx_max.receive(cf)
        if data:
            break
    
    assert len(data) == 4095, "Should receive complete 4095 bytes"
    assert data == max_data, "Data should match exactly"
    logging.info("✓ Maximum length data test passed\n")


def test_invalid_parameters():
    """
    Test invalid parameter handling
    
    Verifies:
    - Empty data rejection
    - Oversized data rejection (>4095 bytes)
    - Invalid flow control parameters
    """
    logging.info("[Test 9] Invalid Parameter Handling")
    
    adapter = CAN_Protocol_Adapter(is_canfd=False)
    
    # Test empty data send
    try:
        adapter.send(bytes())
        assert False, "Should raise ValueError"
    except ValueError as e:
        logging.info(f"✓ Correctly rejected empty data: {e}")
    
    # Test oversized data send
    try:
        adapter.send(bytes(5000))
        assert False, "Should raise ValueError"
    except ValueError as e:
        logging.info(f"✓ Correctly rejected oversized data: {e}")
    
    # Test invalid flow control parameters
    try:
        adapter.create_flow_control_frame(flow_status=5)
        assert False, "Should raise ValueError"
    except ValueError as e:
        logging.info(f"✓ Correctly rejected invalid flow status: {e}")
    
    try:
        adapter.create_flow_control_frame(block_size=300)
        assert False, "Should raise ValueError"
    except ValueError as e:
        logging.info(f"✓ Correctly rejected invalid block size: {e}\n")


def test_state_management():
    """
    Test state management
    
    Verifies:
    - Proper state initialization
    - State reset functionality
    - Invalid state operation prevention
    """
    logging.info("[Test 10] State Management Testing")
    
    tx = CAN_Protocol_Adapter(is_canfd=False)
    rx = CAN_Protocol_Adapter(is_canfd=False)
    
    # Test sending consecutive frames without initialization
    try:
        tx.send_consecutive_frames()
        assert False, "Should raise RuntimeError"
    except RuntimeError as e:
        logging.info(f"✓ Correctly rejected uninitialized consecutive frame send: {e}")
    
    # Test receiving consecutive frame without first frame
    consecutive_frame = bytes([0x21, 0x01, 0x02])  # SN=1 consecutive frame
    try:
        rx.receive(consecutive_frame)
        assert False, "Should raise ProtocolError"
    except ProtocolError as e:
        logging.info(f"✓ Correctly rejected invalid consecutive frame: {e}")
    
    # Test reset functionality
    test_data = bytes(range(20))
    frames = tx.send(test_data)
    rx.receive(frames[0])
    
    assert rx.receiving == True, "Should be in receiving state"
    rx.reset()
    assert rx.receiving == False, "Should not be in receiving state after reset"
    logging.info("✓ State reset functionality working correctly\n")


def run_all_tests():
    """
    Run all integration tests
    
    Executes complete test suite and generates summary report.
    
    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    # Initialize test logger
    test_logger = TestLogger()
    
    test_functions: List[Callable] = [
        test_single_frame_can,
        test_single_frame_canfd,
        test_multi_frame_without_flow_control,
        test_multi_frame_with_block_size,
        test_sequence_error,
        test_frame_length_error,
        test_overflow_flow_control,
        test_edge_cases,
        test_invalid_parameters,
        test_state_management,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in test_functions:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            failed += 1
            logging.error(f"✗ {test_func.__name__} failed: {e}\n")
            import traceback
            logging.error(traceback.format_exc())
        except Exception as e:
            failed += 1
            logging.error(f"✗ {test_func.__name__} exception: {e}\n")
            import traceback
            logging.error(traceback.format_exc())
    
    # Test summary
    logging.info("=" * 80)
    logging.info(f"Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info(f"Total tests: {len(test_functions)}")
    logging.info(f"Passed: {passed}")
    logging.info(f"Failed: {failed}")
    logging.info(f"Success rate: {passed/len(test_functions)*100:.1f}%")
    logging.info("=" * 80)
    
    if failed == 0:
        logging.info("🎉 All tests passed!")
        return 0
    else:
        logging.warning(f"⚠️  {failed} test(s) failed, please check the log")
        return 1


def main():
    """
    Main entry point for integration test suite
    
    Returns:
        int: Exit code
    """
    try:
        return run_all_tests()
    except Exception as e:
        logging.error(f"Test suite failed with exception: {type(e).__name__}: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())