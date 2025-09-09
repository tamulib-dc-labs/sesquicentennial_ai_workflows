from google.cloud import vision
import os


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