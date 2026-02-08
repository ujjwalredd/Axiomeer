#!/bin/bash

# Script to convert markdown product guide to PDF
# Requires: pandoc and texlive (for PDF generation)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCS_DIR="$PROJECT_ROOT/docs"

INPUT_MD="$DOCS_DIR/AXIOMEER_PRODUCT_GUIDE.md"
OUTPUT_PDF="$DOCS_DIR/axiomeer_product_guide.pdf"

echo "===================================="
echo "Axiomeer Product Guide PDF Generator"
echo "===================================="
echo ""

# Check if pandoc is installed
if ! command -v pandoc &> /dev/null; then
    echo "❌ Error: pandoc is not installed"
    echo ""
    echo "To install pandoc:"
    echo "  macOS:   brew install pandoc"
    echo "  Ubuntu:  sudo apt-get install pandoc texlive-latex-base texlive-fonts-recommended texlive-latex-extra"
    echo "  Windows: https://pandoc.org/installing.html"
    exit 1
fi

# Check if input file exists
if [ ! -f "$INPUT_MD" ]; then
    echo "❌ Error: Input file not found: $INPUT_MD"
    exit 1
fi

echo "Input:  $INPUT_MD"
echo "Output: $OUTPUT_PDF"
echo ""
echo "Converting markdown to PDF..."

# Convert with pandoc
pandoc "$INPUT_MD" \
    --from=markdown \
    --to=pdf \
    --output="$OUTPUT_PDF" \
    --pdf-engine=pdflatex \
    --variable=geometry:margin=1in \
    --variable=fontsize:11pt \
    --variable=documentclass:article \
    --variable=colorlinks:true \
    --variable=linkcolor:blue \
    --variable=urlcolor:blue \
    --toc \
    --toc-depth=3 \
    --number-sections \
    --highlight-style=tango \
    --metadata title="Axiomeer Product Guide" \
    --metadata author="Axiomeer Team" \
    --metadata date="February 2026"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Success! PDF generated at:"
    echo "   $OUTPUT_PDF"
    echo ""

    # Get file size
    FILE_SIZE=$(du -h "$OUTPUT_PDF" | cut -f1)
    echo "   File size: $FILE_SIZE"

    # Count pages (if pdfinfo is available)
    if command -v pdfinfo &> /dev/null; then
        PAGE_COUNT=$(pdfinfo "$OUTPUT_PDF" 2>/dev/null | grep "Pages:" | awk '{print $2}')
        echo "   Pages: $PAGE_COUNT"
    fi
else
    echo ""
    echo "❌ Error: PDF generation failed"
    exit 1
fi
