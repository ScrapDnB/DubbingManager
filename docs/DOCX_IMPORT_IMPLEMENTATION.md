# DOCX Import Feature - Implementation Summary

## Overview
Added flexible DOCX import functionality with customizable column mapping, preview, and support for split timing in a single column.

## Files Created

### 1. `services/docx_import_service.py`
Core service for DOCX import with the following features:
- **Table extraction**: Extracts tables from DOCX files
- **Auto-detection**: Automatically detects column types based on headers
- **Flexible mapping**: Supports custom column mapping for each field type
- **Split timing support**: Parses timing in single column with configurable separators
- **Time parsing**: Supports multiple time formats (SRT, ASS, MM:SS, etc.)
- **Preview generation**: Creates preview data for validation before import

**Column Types:**
- `character` - Character name
- `time_start` - Start time (separate column)
- `time_end` - End time (separate column)
- `time_split` - Combined timing in one column (e.g., "00:00:01,000 - 00:00:03,000")
- `text` - Replica text

**Default Separators:** `-`, `–` (en-dash), `—` (em-dash), `|`, `/`

### 2. `ui/dialogs/docx_import.py`
Dialog window for DOCX import with:
- **File selection**: Button to choose DOCX file
- **Auto-detect button**: Automatically maps columns based on headers
- **Manual mapping**: Dropdown combos for each field type
- **Separator configuration**: Text field to customize timing separators
- **Live preview**: Table showing how data will be imported (6 columns)
- **Status indicators**: Visual feedback for valid/invalid rows
- **Statistics**: Count of valid and problematic rows

### 3. `tests/test_docx_import.py`
Comprehensive test suite covering:
- Table extraction from DOCX
- Column auto-detection
- Parsing with custom mapping
- Split time parsing with multiple separators
- Custom separator configuration
- Parsing with split timing
- Time format parsing
- Preview data generation (both separate and split timing)
- Edge cases (empty files, missing columns)

**11 tests, all passing**

### 4. `docs/DOCX_IMPORT.md`
User documentation in Russian explaining:
- File format requirements
- Supported time formats
- Configurable separators
- Step-by-step usage guide
- Auto-detection header examples
- Sample table formats (both separate and split timing)

## Files Modified

### 1. `requirements.txt`
Added `python-docx>=1.0.0` dependency

### 2. `services/__init__.py`
Exported `DocxImportService`

### 3. `ui/dialogs/__init__.py`
Exported `DocxImportDialog`

### 4. `ui/main_window.py`
- Added "+ .DOCX" button in episode control panel
- Implemented `import_docx()` method to handle DOCX import
- Integrated with episode caching system

## Key Features

### 1. Flexible Column Mapping
Users can map any column in the DOCX table to any field type:
- Character name
- Start/End times (separate columns)
- Combined timing (single column with separator)
- Text content

### 2. Split Timing Support
Supports timing in a single column with configurable separators:
- Default: `-`, `–`, `—`, `|`, `/`
- Customizable in the import dialog
- Example: `00:00:01,000 - 00:00:03,000`

### 3. Auto-Detection
The system automatically recognizes column types by analyzing headers:
- Russian: "персонаж", "начало", "конец", "тайминг", "текст"
- English: "character", "start", "end", "timing", "text"
- And many more variations

### 4. Live Preview
Before importing, users see:
- How data will be parsed
- Parsed time values in seconds
- Visual indicators for problematic rows
- Statistics on valid/invalid entries

### 5. Multiple Time Formats
Supports various time formats:
- `HH:MM:SS,mmm` (SRT style)
- `HH:MM:SS.mmm`
- `MM:SS,mmm`
- `MM:SS`

### 6. Undo Support
Import operations can be undone with Ctrl+Z

## Testing

All tests pass:
```
tests/test_docx_import.py::TestDocxImportService::test_extract_tables_from_docx PASSED
tests/test_docx_import.py::TestDocxImportService::test_detect_columns_auto PASSED
tests/test_docx_import.py::TestDocxImportService::test_parse_with_mapping PASSED
tests/test_docx_import.py::TestDocxImportService::test_parse_split_time PASSED
tests/test_docx_import.py::TestDocxImportService::test_parse_split_time_with_custom_separators PASSED
tests/test_docx_import.py::TestDocxImportService::test_parse_with_split_timing PASSED
tests/test_docx_import.py::TestDocxImportService::test_parse_time_formats PASSED
tests/test_docx_import.py::TestDocxImportService::test_get_preview_data PASSED
tests/test_docx_import.py::TestDocxImportService::test_get_preview_data_split_time PASSED
tests/test_docx_import.py::TestDocxImportService::test_empty_file PASSED
tests/test_docx_import.py::TestDocxImportService::test_missing_columns PASSED
```

## Usage Flow

1. User clicks "+ .DOCX" button
2. Selects DOCX file from file dialog
3. Dialog opens with column mapping interface
4. Auto-detection runs automatically
5. User reviews preview table (6 columns including split timing)
6. User adjusts mapping and separators if needed
7. User clicks "Import"
8. Enters episode number
9. Data is imported and episode is created

## Architecture

Follows the existing Service Layer pattern:
```
UI (MainWindow) → DocxImportDialog → DocxImportService → Data
```

## Dependencies

- `python-docx>=1.0.0` - For reading DOCX files
- No other external dependencies (uses existing PySide6, etc.)

## Backward Compatibility

- No breaking changes to existing functionality
- Optional feature that doesn't affect ASS/SRT imports
- Graceful degradation if python-docx is not installed
