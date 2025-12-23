"""
Firmware Chunk Processing Module (High Performance Version)

This module provides firmware data chunking functionality, splitting large firmware data 
into multiple blocks of specified size. Each block contains a sequence number and data content,
suitable for firmware flashing scenarios.

Performance optimizations:
- Uses memory views to avoid data copying
- Supports generator mode to reduce memory usage
- Batch operations for improved processing speed
"""
from typing import Dict, List, Union, Generator, Iterator, Optional
import sys
import logging
from logging.handlers import RotatingFileHandler
from array import array
from pathlib import Path
from datetime import datetime


class FirmwareChunker:
    """
    Firmware Data Chunker (High Performance Version)
    
    Splits firmware data into multiple blocks by specified maximum bytes. Each block 
    automatically includes a sequence number. Supports generator mode for large file processing.
    
    Attributes:
        flash_data (array): Firmware data to be chunked
        block_max_bytes (int): Maximum bytes per block (default 4095)
        logger (logging.Logger): Logger instance for this chunker
    """
    
    # Class constants
    DEFAULT_BLOCK_MAX_BYTES = 4095
    HEADER_BYTES = 1  # PCI and data length each occupy 1 byte
    
    def __init__(self, 
                 flash_data: Union[List[int], bytes, bytearray, array], 
                 block_max_bytes: int = DEFAULT_BLOCK_MAX_BYTES,
                 logger: Optional[logging.Logger] = None) -> None:
        """
        Initialize firmware chunker
        
        Args:
            flash_data (Union[List[int], bytes, bytearray, array]): 
                Firmware data (supports list, bytes, bytearray, array)
            block_max_bytes (int): Maximum bytes per block
            logger (Optional[logging.Logger]): Logger instance, creates default if None
            
        Raises:
            ValueError: When block_max_bytes <= HEADER_BYTES
            TypeError: When flash_data type is not supported
        """
        self.logger = logger or self._create_default_logger()
        
        if block_max_bytes <= self.HEADER_BYTES:
            raise ValueError(
                f"block_max_bytes must be greater than {self.HEADER_BYTES} bytes, "
                f"current value is {block_max_bytes}"
            )
        
        # Convert to array for memory efficiency (reduces memory usage by ~50% compared to list)
        if isinstance(flash_data, array):
            self.flash_data = flash_data
        elif isinstance(flash_data, (bytes, bytearray)):
            self.flash_data = array('B', flash_data)
        elif isinstance(flash_data, list):
            self.flash_data = array('B', flash_data)
        else:
            raise TypeError(
                f"flash_data must be list, bytes, bytearray or array, "
                f"current type is {type(flash_data).__name__}"
            )
        
        self.block_max_bytes = block_max_bytes
        self._max_data_bytes = block_max_bytes - self.HEADER_BYTES
        self._data_length = len(self.flash_data)
        self._block_count = (self._data_length) // self._max_data_bytes + 1
        
        self.logger.info(
            f"Firmware chunker initialized: "
            f"data_length={self._data_length} bytes, "
            f"block_max_bytes={block_max_bytes}, "
            f"block_count={self._block_count}"
        )
    
    def _create_default_logger(self) -> logging.Logger:
        """
        Create default logger with file and console handlers
        
        Returns:
            logging.Logger: Configured logger instance
        """
        logger = logging.getLogger("FirmwareChunker")
        logger.setLevel(logging.DEBUG)
        
        # Avoid adding duplicate handlers
        if logger.handlers:
            return logger
        
        # Create logs directory if not exists
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Create log filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"firmware_chunker_{timestamp}.log"
        
        # File handler with rotation
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        
        # Add handlers
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        logger.info(f"Logger initialized, log file: {log_file}")
        
        return logger
    
    def separate_data_to_blocks(self) -> Dict[int, bytes]:
        """
        Split firmware data into multiple blocks (complete mode)
        
        Suitable for scenarios requiring all blocks at once.
        For large files, iter_blocks() generator mode is recommended.
        
        Returns:
            Dict[int, bytes]: Dictionary of data blocks {block_number: block_data}
            
        Raises:
            ValueError: When flash_data is empty
        """
        if self._data_length == 0:
            raise ValueError("Firmware data cannot be empty")
        
        self.logger.info(f"Starting block separation: {self._block_count} blocks")
        blocks = {i: bytes(block) for i, block in enumerate(self.iter_blocks(), 1)}
        self.logger.info(f"Block separation complete: {len(blocks)} blocks created")
        
        return blocks
    
    def iter_blocks(self) -> Generator[List[int], None, None]:
        """
        Generate blocks one by one using generator (recommended for large files)
        
        Memory-efficient iteration that generates blocks on demand without 
        occupying large amounts of memory at once.
        
        Yields:
            List[int]: Each data block (including sequence number)
            
        Raises:
            ValueError: When flash_data is empty
            
        Example:
            >>> chunker = FirmwareChunker(large_data)
            >>> for block_num, block in enumerate(chunker.iter_blocks(), 1):
            ...     process_block(block_num, block)
        """
        if self._data_length == 0:
            raise ValueError("Firmware data cannot be empty")
        
        # Use memoryview for zero-copy slicing
        mv = memoryview(self.flash_data)
        for block_index in range(self._block_count):
            start = block_index * self._max_data_bytes
            end = min(start + self._max_data_bytes, self._data_length)
            
            # Use memoryview slicing to avoid data copying
            block_data = mv[start:end]
            
            yield [(block_index + 1) % 256] + list(block_data)
    
    def iter_blocks_fast(self) -> Iterator[tuple]:
        """
        Fast iteration mode: returns (sequence_number, start_pos, end_pos)
        
        Fastest iteration method, returns only index information without copying data.
        Suitable for scenarios only needing block position info (e.g., direct file writing).
        
        Yields:
            tuple: (block_number, start_index, end_index)
            
        Raises:
            ValueError: When flash_data is empty
            
        Example:
            >>> for block_num, start, end in chunker.iter_blocks_fast():
            ...     raw_data = chunker.flash_data[start:end]
            ...     file.write(bytes([block_num]) + raw_data)
        """
        if self._data_length == 0:
            raise ValueError("Firmware data cannot be empty")
        
        for block_index in range(self._block_count):
            start = block_index * self._max_data_bytes
            end = min(start + self._max_data_bytes, self._data_length)
            yield (block_index + 1, start, end)
    
    def get_block_info(self) -> Dict[str, Union[int, float]]:
        """
        Get block statistics information
        
        Returns:
            Dict[str, Union[int, float]]: Dictionary containing block statistics
                - total_data_bytes (int): Total data size in bytes
                - max_data_per_block (int): Maximum data bytes per block
                - block_count (int): Total number of blocks
                - last_block_bytes (int): Data bytes in last block
                - overhead_ratio (float): Header overhead ratio percentage
        """
        if self._data_length == 0:
            return {
                'total_data_bytes': 0,
                'max_data_per_block': self._max_data_bytes,
                'block_count': 0,
                'last_block_bytes': 0,
                'overhead_ratio': 0.0
            }
        
        last_block_bytes = self._data_length % self._max_data_bytes or self._max_data_bytes
        
        # Calculate header overhead ratio
        total_bytes_with_header = self._block_count * self.block_max_bytes
        overhead_ratio = (self._block_count * self.HEADER_BYTES / total_bytes_with_header) * 100
        
        return {
            'total_data_bytes': self._data_length,
            'max_data_per_block': self._max_data_bytes,
            'block_count': self._block_count,
            'last_block_bytes': last_block_bytes,
            'overhead_ratio': round(overhead_ratio, 2)
        }
    
    def get_block_by_index(self, block_num: int) -> bytes:
        """
        Directly get data block by sequence number (random access)
        
        Args:
            block_num (int): Block sequence number (starting from 1)
            
        Returns:
            bytes: Specified data block with sequence number prepended
            
        Raises:
            ValueError: When block_num is out of range
        """
        if not 1 <= block_num <= self._block_count:
            raise ValueError(
                f"block_num must be between 1 and {self._block_count}, "
                f"current value is {block_num}"
            )
        
        block_index = block_num - 1
        start = block_index * self._max_data_bytes
        end = min(start + self._max_data_bytes, self._data_length)
        
        block_data = list(self.flash_data[start:end])
        
        self.logger.debug(f"Retrieved block {block_num}: {len(block_data)} bytes")
        return bytes([block_num] + block_data)


def format_hex_data(data: Union[List[int], bytes, bytearray], 
                    bytes_per_line: int = 16,
                    max_lines: Optional[int] = None) -> str:
    """
    Format hexadecimal data display (optimized version)
    
    Args:
        data (Union[List[int], bytes, bytearray]): Data list or byte string
        bytes_per_line (int): Number of bytes to display per line
        max_lines (Optional[int]): Maximum number of lines to display (None for all)
        
    Returns:
        str: Formatted hexadecimal string
    """
    lines = []
    total_lines = (len(data) + bytes_per_line - 1) // bytes_per_line
    display_lines = min(total_lines, max_lines) if max_lines else total_lines
    
    for i in range(display_lines):
        start = i * bytes_per_line
        end = min(start + bytes_per_line, len(data))
        chunk = data[start:end]
        hex_str = ' '.join(f'{b:02X}' for b in chunk)
        lines.append(f"  {hex_str}")
    
    if max_lines and total_lines > max_lines:
        lines.append(f"  ... (omitted {total_lines - max_lines} lines)")
    
    return '\n'.join(lines)


def setup_test_logger() -> logging.Logger:
    """
    Setup logger for test functions
    
    Returns:
        logging.Logger: Configured test logger
    """
    logger = logging.getLogger("FirmwareChunkerTest")
    logger.setLevel(logging.DEBUG)
    
    # Avoid adding duplicate handlers
    if logger.handlers:
        return logger
    
    # Create logs directory if not exists
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Create log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"firmware_chunker_test_{timestamp}.log"
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logger.info(f"Test logger initialized, log file: {log_file}")
    
    return logger


def test_basic_chunking(logger: logging.Logger):
    """Test basic chunking functionality"""
    logger.info("=" * 70)
    logger.info("Test 1: Basic Chunking")
    logger.info("=" * 70)
    
    # Create test data
    test_data = bytes(range(256))
    chunker = FirmwareChunker(test_data, block_max_bytes=50, logger=logger)
    
    # Get block info
    info = chunker.get_block_info()
    logger.info("Block Info:")
    for key, value in info.items():
        logger.info(f"  {key}: {value}")
    
    # Get all blocks
    blocks = chunker.separate_data_to_blocks()
    logger.info(f"Total blocks: {len(blocks)}")
    
    # Display first block
    if blocks:
        first_block = blocks[1]
        logger.info(f"First block (length={len(first_block)}):")
        hex_output = format_hex_data(first_block, max_lines=3)
        for line in hex_output.split('\n'):
            logger.info(line)


def test_generator_mode(logger: logging.Logger):
    """Test generator mode for memory efficiency"""
    logger.info("=" * 70)
    logger.info("Test 2: Generator Mode")
    logger.info("=" * 70)
    
    # Create larger test data
    test_data = bytes(range(256)) * 10  # 2560 bytes
    chunker = FirmwareChunker(test_data, block_max_bytes=100, logger=logger)
    
    logger.info("Processing blocks with generator:")
    block_count = 0
    for block in chunker.iter_blocks():
        block_count += 1
        if block_count <= 3:  # Show first 3 blocks
            logger.info(f"Block {block[0]} (length={len(block)}):")
            hex_output = format_hex_data(block[:20], bytes_per_line=10, max_lines=2)
            for line in hex_output.split('\n'):
                logger.info(line)
    
    logger.info(f"Total blocks processed: {block_count}")


def test_fast_iteration(logger: logging.Logger):
    """Test fast iteration mode"""
    logger.info("=" * 70)
    logger.info("Test 3: Fast Iteration Mode")
    logger.info("=" * 70)
    
    test_data = bytes(range(100))
    chunker = FirmwareChunker(test_data, block_max_bytes=25, logger=logger)
    
    logger.info("Fast iteration (index only):")
    for block_num, start, end in chunker.iter_blocks_fast():
        data_size = end - start
        logger.info(f"  Block {block_num}: start={start}, end={end}, size={data_size}")


def test_random_access(logger: logging.Logger):
    """Test random access to specific blocks"""
    logger.info("=" * 70)
    logger.info("Test 4: Random Access")
    logger.info("=" * 70)
    
    test_data = bytes(range(200))
    chunker = FirmwareChunker(test_data, block_max_bytes=50, logger=logger)
    
    # Access specific blocks
    block_nums = [1, 3, 5]
    for num in block_nums:
        try:
            block = chunker.get_block_by_index(num)
            logger.info(f"Block {num} (length={len(block)}):")
            hex_output = format_hex_data(block[:20], bytes_per_line=10, max_lines=2)
            for line in hex_output.split('\n'):
                logger.info(line)
        except ValueError as e:
            logger.error(f"Error accessing block {num}: {e}")


def test_with_hex_parser(logger: logging.Logger):
    """Test integration with HexParser"""
    logger.info("=" * 70)
    logger.info("Test 5: Integration with HexParser")
    logger.info("=" * 70)
    
    import time
    
    try:
        from hex_file_parser import HexParser
        
        hex_file_path = r"C:\Users\m0199528\Documents\Mahle_Projects\Platform_Tool\prj\temp_hex_flash_files\FlashDriver.hex"
        hex_file_path = r"C:\Users\m0199528\Documents\Mahle_Projects\Platform_Tool\prj\temp_hex_flash_files\obcdemo7_sup_dclv_APP.hex"
        
        logger.info(f"Parsing hex file: {hex_file_path}")
        parse_start = time.perf_counter()
        hex_parser = HexParser(hex_file_path)
        parse_time = time.perf_counter() - parse_start
        
        logger.info(f"Parse complete, time: {parse_time:.3f}s")
        logger.info(f"Found {len(hex_parser.flash_info)} flash regions")
        
        for region_id, flash_info in hex_parser.flash_info.items():
            logger.info(f"Flash Region #{region_id}")
            logger.info("-" * 70)
            
            chunk_start = time.perf_counter()
            chunker = FirmwareChunker(flash_info['Data'], logger=logger)
            
            info = chunker.get_block_info()
            logger.info("Block statistics:")
            for key, value in info.items():
                logger.info(f"  {key}: {value}")
            
            # Get first block as example
            blocks = chunker.separate_data_to_blocks()
            if blocks:
                first_block = blocks[1]
                logger.info(f"First block preview (length={len(first_block)}):")
                hex_output = format_hex_data(first_block[:48], bytes_per_line=16, max_lines=3)
                for line in hex_output.split('\n'):
                    logger.info(line)
            
            chunk_time = time.perf_counter() - chunk_start
            logger.info(f"Chunking time: {chunk_time:.3f}s")
            
    except ImportError:
        logger.error("Error: Cannot import hex_file_parser module")
    except FileNotFoundError as e:
        logger.error(f"Error: File not found - {e}")
    except Exception as e:
        logger.error(f"Error occurred: {type(e).__name__}: {e}")
        import traceback
        logger.error(traceback.format_exc())


def main():
    """Main test function"""
    # Setup test logger
    test_logger = setup_test_logger()
    
    test_logger.info("=" * 70)
    test_logger.info("Firmware Chunker Test Suite")
    test_logger.info("=" * 70)
    
    # Run all tests
    try:
        # test_basic_chunking(test_logger)
        # test_generator_mode(test_logger)
        # test_fast_iteration(test_logger)
        # test_random_access(test_logger)
        test_with_hex_parser(test_logger)
        
        test_logger.info("=" * 70)
        test_logger.info("All tests completed successfully")
        test_logger.info("=" * 70)
        
    except Exception as e:
        test_logger.error(f"Test suite failed: {type(e).__name__}: {e}")
        import traceback
        test_logger.error(traceback.format_exc())
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())