from google.cloud import vision
import os
import html
from datetime import datetime
from PIL import Image


class CloudViz:
    def __init__(self):
        self.client = vision.ImageAnnotatorClient.from_service_account_json(
            os.environ.get('GOOGLE_CLOUD_VIZ_CREDENTIALS')
        )

    def extract_text(self, image_path):
        """Extract just the text of an image.

        args:
            image_path (str): path to an image

        returns:
            str: text in the image
        """
        with open(image_path, 'rb') as image_file:
            content = image_file.read()

        image = vision.Image(content=content)
        response = self.client.document_text_detection(image=image)
        texts = response.text_annotations
        if texts:
            return texts[0].description
        return ""

    def extract_text_with_boxes(self, image_path):
        """Extract text with bounding box coordinates"""
        with open(image_path, 'rb') as image_file:
            content = image_file.read()

        image = vision.Image(content=content)
        response = self.client.document_text_detection(image=image)

        results = []

        # Skip the first annotation since it's in the full text
        for text in response.text_annotations[1:]:
            vertices = text.bounding_poly.vertices
            x_coords = [vertex.x for vertex in vertices]
            y_coords = [vertex.y for vertex in vertices]

            x = min(x_coords)
            y = min(y_coords)
            w = max(x_coords) - x
            h = max(y_coords) - y

            results.append({
                'text': text.description,
                'x': x,
                'y': y,
                'w': w,
                'h': h,
                'confidence': getattr(text, 'confidence', None)
            })

        return results

    def extract_structured_text(self, image_path):
        """Extract text with detailed structure (paragraphs, words, symbols)"""
        with open(image_path, 'rb') as image_file:
            content = image_file.read()
        image = vision.Image(content=content)
        response = self.client.document_text_detection(image=image)
        if not response.full_text_annotation:
            return []
        results = []
        for page in response.full_text_annotation.pages:
            for block in page.blocks:
                for paragraph in block.paragraphs:
                    for word in paragraph.words:
                        word_text = ''.join([symbol.text for symbol in word.symbols])

                        vertices = word.bounding_box.vertices
                        x_coords = [vertex.x for vertex in vertices]
                        y_coords = [vertex.y for vertex in vertices]

                        x = min(x_coords)
                        y = min(y_coords)
                        w = max(x_coords) - x
                        h = max(y_coords) - y

                        results.append({
                            'text': word_text,
                            'x': x,
                            'y': y,
                            'w': w,
                            'h': h,
                            'confidence': word.confidence
                        })
        return results

    def to_hocr(self, image_path, image_width=None, image_height=None):
        """Convert OCR results to hOCR format"""
        if image_width is None or image_height is None:
            with Image.open(image_path) as img:
                image_width, image_height = img.size

        with open(image_path, 'rb') as image_file:
            content = image_file.read()

        image = vision.Image(
            content=content
        )
        response = self.client.document_text_detection(
            image=image
        )

        if not response.full_text_annotation:
            return self._empty_hocr(image_path, image_width, image_height)

        hocr_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"',
            '    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">',
            '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">',
            '<head>',
            '<meta http-equiv="Content-Type" content="text/html;charset=utf-8" />',
            '<meta name="ocr-system" content="Google Cloud Vision API" />',
            f'<meta name="ocr-creation-date" content="{datetime.now().isoformat()}" />',
            '<title>hOCR Output</title>',
            '</head>',
            '<body>',
            f'<div class="ocr_page" id="page_1" title="bbox 0 0 {image_width} {image_height}; ppageno 0">'
        ]

        page_num = 1
        block_num = 1
        par_num = 1
        line_num = 1
        word_num = 1

        for page in response.full_text_annotation.pages:
            for block in page.blocks:
                block_vertices = block.bounding_box.vertices
                block_x1 = min(v.x for v in block_vertices)
                block_y1 = min(v.y for v in block_vertices)
                block_x2 = max(v.x for v in block_vertices)
                block_y2 = max(v.y for v in block_vertices)

                hocr_lines.append(
                    f'<div class="ocr_carea" id="carea_{page_num}_{block_num}" title="bbox {block_x1} {block_y1} {block_x2} {block_y2}">')

                for paragraph in block.paragraphs:
                    par_vertices = paragraph.bounding_box.vertices
                    par_x1 = min(v.x for v in par_vertices)
                    par_y1 = min(v.y for v in par_vertices)
                    par_x2 = max(v.x for v in par_vertices)
                    par_y2 = max(v.y for v in par_vertices)

                    hocr_lines.append(
                        f'<p class="ocr_par" id="par_{page_num}_{par_num}" title="bbox {par_x1} {par_y1} {par_x2} {par_y2}">')

                    current_line_words = []
                    current_line_y = None
                    line_threshold = 10  # pixels

                    for word in paragraph.words:
                        word_vertices = word.bounding_box.vertices
                        word_y = min(v.y for v in word_vertices)

                        if current_line_y is None or abs(word_y - current_line_y) <= line_threshold:
                            current_line_words.append(word)
                            if current_line_y is None:
                                current_line_y = word_y
                        else:
                            if current_line_words:
                                hocr_lines.append(self._format_hocr_line(current_line_words, line_num, word_num))
                                word_num += len(current_line_words)
                                line_num += 1

                            current_line_words = [word]
                            current_line_y = word_y

                    if current_line_words:
                        hocr_lines.append(self._format_hocr_line(current_line_words, line_num, word_num))
                        word_num += len(current_line_words)
                        line_num += 1

                    hocr_lines.append('</p>')
                    par_num += 1

                hocr_lines.append('</div>')
                block_num += 1

        hocr_lines.extend([
            '</div>',
            '</body>',
            '</html>'
        ])

        return '\n'.join(hocr_lines)

    def _format_hocr_line(self, words, line_num, start_word_num):
        """Format a line of words for hOCR"""
        all_vertices = []
        for word in words:
            all_vertices.extend(word.bounding_box.vertices)

        line_x1 = min(v.x for v in all_vertices)
        line_y1 = min(v.y for v in all_vertices)
        line_x2 = max(v.x for v in all_vertices)
        line_y2 = max(v.y for v in all_vertices)

        line_html = [
            f'<span class="ocr_line" id="line_{line_num}" title="bbox {line_x1} {line_y1} {line_x2} {line_y2}">'
        ]

        word_num = start_word_num
        for word in words:
            word_text = ''.join([symbol.text for symbol in word.symbols])
            word_vertices = word.bounding_box.vertices

            word_x1 = min(v.x for v in word_vertices)
            word_y1 = min(v.y for v in word_vertices)
            word_x2 = max(v.x for v in word_vertices)
            word_y2 = max(v.y for v in word_vertices)

            confidence = int(word.confidence * 100) if word.confidence else 0

            escaped_text = html.escape(word_text)
            line_html.append(
                f'<span class="ocrx_word" id="word_{word_num}" title="bbox {word_x1} {word_y1} {word_x2} {word_y2}; x_wconf {confidence}">{escaped_text}</span>')
            word_num += 1
        line_html.append('</span>')
        return ' '.join(line_html)

    def _empty_hocr(self, width, height):
        """Return empty hOCR structure when no text found"""

        return f'''<?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
            "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
            <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
            <head>
            <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
            <meta name="ocr-system" content="Google Cloud Vision API" />
            <meta name="ocr-creation-date" content="{datetime.now().isoformat()}" />
            <title>hOCR Output</title>
            </head>
            <body>
            <div class="ocr_page" id="page_1" title="bbox 0 0 {width} {height}; ppageno 0">
            </div>
            </body>
            </html>'''

    def save_hocr(self, image_path, output_path, image_width=None, image_height=None):
        """Generate and save hOCR to file"""
        hocr_content = self.to_hocr(image_path, image_width, image_height)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(hocr_content)
        return output_path


if __name__ == '__main__':
    cloud_viz = CloudViz()
    # How to get just the text
    print(
        "=== Just Text ==="
    )
    text = cloud_viz.extract_text('test_files/amctrial_mcinnis_0004.jpg')
    print(
        text[:200] + "..." if len(text) > 200 else text
    )

    # Method 1: Individual text elements with boxes
    print(
        "\n=== Text with Bounding Boxes ==="
    )
    text_boxes = cloud_viz.extract_text_with_boxes(
        'test_files/amctrial_mcinnis_0004.jpg'
    )
    for item in text_boxes[:5]:
        print(f"Text: '{item['text']}' at ({item['x']}, {item['y']}) size: {item['w']}x{item['h']}")

    # Method 2: Structured extraction (word by word)
    print("\n=== Structured Text (Word Level) ===")
    structured_text = cloud_viz.extract_structured_text('test_files/amctrial_mcinnis_0004.jpg')
    for item in structured_text[:5]:
        print(
            f"Word: '{item['text']}' at ({item['x']}, {item['y']}) size: {item['w']}x{item['h']} confidence: {item['confidence']:.2f}")

    print("\n=== Generate hOCR ===")
    # Method 3: Generate hOCR format
    hocr_output = cloud_viz.to_hocr('test_files/amctrial_mcinnis_0004.jpg')
    print("hOCR generated successfully!")
    print(f"Preview (first 500 chars):\n{hocr_output[:500]}...")

    # Method 3.5: Save to file
    cloud_viz.save_hocr('test_files/amctrial_mcinnis_0004.jpg', 'output.hocr')
    print("\nhOCR saved to output.hocr")