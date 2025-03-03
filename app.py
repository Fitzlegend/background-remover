from flask import Flask, jsonify, request
from rembg import remove
from PIL import Image
import io
import base64
import zipfile
import logging
import traceback

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('BackgroundRemover')

@app.route('/')
def index():
    logger.info("Serving index.html")
    return app.send_static_file('index.html')

@app.route('/process', methods=['POST'])
def process_images():
    try:
        logger.info("Starting /process endpoint")
        if 'files' not in request.files:
            logger.warning("No files uploaded")
            return jsonify({'error': 'No files uploaded', 'logs': []}), 400

        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            logger.warning("No valid files provided")
            return jsonify({'error': 'No files provided', 'logs': []}), 400

        processed_files = []
        logs = []
        previews = []

        for file in files:
            try:
                logger.info(f"Processing {file.filename}")
                input_image = Image.open(file.stream)
                output_image = remove(input_image)
                output_buffer = io.BytesIO()
                output_image.save(output_buffer, format='PNG')
                output_buffer.seek(0)
                img_base64 = base64.b64encode(output_buffer.getvalue()).decode('utf-8')
                processed_files.append((file.filename.replace('.', '_no-bg.'), output_buffer))
                previews.append({'filename': file.filename, 'image': img_base64})
                logs.append(f"Processed {file.filename} successfully")
            except Exception as e:
                error_msg = f"Error processing {file.filename}: {str(e)}"
                logger.error(error_msg)
                logs.append(error_msg)

        if not processed_files:
            logger.warning("No images processed successfully")
            return jsonify({'error': 'No images processed successfully', 'logs': logs, 'previews': []}), 500

        logger.info("Creating ZIP file")
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for filename, buffer in processed_files:
                zip_file.writestr(filename, buffer.getvalue())
        zip_buffer.seek(0)
        zip_base64 = base64.b64encode(zip_buffer.getvalue()).decode('utf-8')

        logger.info("Returning JSON response")
        return jsonify({
            'previews': previews,
            'zip': zip_base64,
            'logs': logs
        })
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return jsonify({'error': f'Server error: {str(e)}', 'logs': [error_msg], 'previews': []}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)