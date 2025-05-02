@echo off
echo Building MCP-Hive with packaged backend (Groq-only version with enhanced dependencies)...

echo Step 1: Building backend executable with all required dependencies
cd Hive
python build_executable.py
if %ERRORLEVEL% NEQ 0 (
    echo Error building backend executable
    exit /b %ERRORLEVEL%
)
cd ..

echo Step 2: Building Electron app
cd MCP-Hive-Desktop
npm install
npm run build:app
if %ERRORLEVEL% NEQ 0 (
    echo Error building Electron app
    exit /b %ERRORLEVEL%
)
cd ..

echo Build complete! The packaged application is available in MCP-Hive-Desktop\dist
echo.
echo Note: This version supports only the Groq LLM provider with additional capabilities like LangChain and document processing. 