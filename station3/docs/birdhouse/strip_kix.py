# chatGPT tried to strip all the kix formatting from Anleitung_Eigenbau_v3.html and convert it to markdown, but this failed
import sys
import os
from bs4 import BeautifulSoup
import re

def html_to_markdown(html):
    soup = BeautifulSoup(html, 'html.parser')

    # Remove unwanted tags and attributes
    for tag in soup(['style', 'script', 'meta', 'link']):
        tag.decompose()

    for tag in soup.find_all(True):
        # Remove Google Docs-specific and inline styling
        if 'class' in tag.attrs:
            tag['class'] = [cls for cls in tag['class'] if not cls.startswith('kix')]
            if not tag['class']:
                del tag['class']
        if 'style' in tag.attrs:
            del tag['style']
        if 'id' in tag.attrs and tag['id'].startswith('kix'):
            del tag['id']

    # Convert headings
    for i in range(1, 7):
        for tag in soup.find_all(f'h{i}'):
            tag.insert_before(f"{'#' * i} {tag.get_text(strip=True)}\n\n")
            tag.decompose()

    # Convert paragraphs
    for tag in soup.find_all('p'):
        text = tag.get_text(strip=True)
        if text:
            tag.insert_before(f"{text}\n\n")
        tag.decompose()

    # Convert images
    for img in soup.find_all('img'):
        alt = img.get('alt', 'Image')
        src = img.get('src', '')
        img.insert_before(f"![{alt}]({src})\n\n")
        img.decompose()

    # Convert links
    for a in soup.find_all('a'):
        href = a.get('href', '')
        text = a.get_text(strip=True)
        a.insert_before(f"[{text}]({href})")
        a.decompose()

    # Convert tables
    markdown = ""
    for table in soup.find_all('table'):
        rows = table.find_all('tr')
        table_data = []
        for row in rows:
            cols = row.find_all(['td', 'th'])
            table_data.append([col.get_text(strip=True) for col in cols])
        if table_data:
            # Header row
            markdown += '| ' + ' | '.join(table_data[0]) + ' |\n'
            markdown += '| ' + ' | '.join(['---'] * len(table_data[0])) + ' |\n'
            # Body rows
            for row in table_data[1:]:
                markdown += '| ' + ' | '.join(row) + ' |\n'
        table.decompose()

    # Remaining text
    markdown += soup.get_text(separator='', strip=True)

    return markdown

# Command-line entry point
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} yourfile.html")
        sys.exit(1)

    input_file = sys.argv[1]

    if not os.path.isfile(input_file):
        print(f"Error: File '{input_file}' does not exist.")
        sys.exit(1)

    with open(input_file, "r", encoding="utf-8") as f:
        html = f.read()

    markdown = html_to_markdown(html)

    output_file = os.path.splitext(input_file)[0] + ".md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(markdown)

    print(f"Converted '{input_file}' to '{output_file}'")
