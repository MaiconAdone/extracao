import os
import io
import boto3
from flask import Flask, request, render_template

app = Flask(__name__)

def extract_text_from_image(image):
    # Configurar as credenciais da AWS (substitua pelos seus próprios valores)
    access_key_id = 'xxxxxxxxxxxx'
    secret_access_key ='xxxxxxxxxxxx'
    region_name = 'xxxxxxxxxxxx'

    # Configurar o cliente Textract
    client = boto3.client('textract', region_name=region_name, aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key)

    # Ler a imagem e processar usando o Textract
    with open(image, 'rb') as file:
        img_test = file.read()
        bytes_test = bytearray(img_test)

    response = client.analyze_document(Document={'Bytes': bytes_test}, FeatureTypes=['FORMS'])

    # Extrair os resultados
    blocks = response['Blocks']
    key_map = {}
    value_map = {}
    block_map = {}
    for block in blocks:
        block_id = block['Id']
        block_map[block_id] = block
        if block['BlockType'] == "KEY_VALUE_SET":
            if 'KEY' in block['EntityTypes']:
                key_map[block_id] = block
            else:
                value_map[block_id] = block

    kvs = {}
    for block_id, key_block in key_map.items():
        value_block = find_value_block(key_block, value_map)
        key = get_text(key_block, block_map)
        val = get_text(value_block, block_map)
        kvs[key] = val

    return kvs

def find_value_block(key_block, value_map):
    for relationship in key_block['Relationships']:
        if relationship['Type'] == 'VALUE':
            for value_id in relationship['Ids']:
                value_block = value_map[value_id]
    return value_block

def get_text(result, blocks_map):
    text = ''
    if 'Relationships' in result:
        for relationship in result['Relationships']:
            if relationship['Type'] == 'CHILD':
                for child_id in relationship['Ids']:
                    word = blocks_map[child_id]
                    if word['BlockType'] == 'WORD':
                        text += word['Text'] + ' '
                    if word['BlockType'] == 'SELECTION_ELEMENT':
                        if word['SelectionStatus'] == 'SELECTED':
                            text += 'X '

    return text

def compare_faces(image_path1, image_path2):
    # Configurar as credenciais da AWS (substitua pelos seus próprios valores)
    access_key_id = 'xxxxxxxxxxxx'
    secret_access_key ='xxxxxxxxxxxx'
    region_name = 'xxxxxxxxxxxx'

    # Configurar o cliente Rekognition
    rekognition_client = boto3.client('rekognition', region_name=region_name, aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key)

    with open(image_path1, 'rb') as cnh_image_file:
        cnh_image_bytes = cnh_image_file.read()

    with open(image_path2, 'rb') as selfie_image_file:
        selfie_image_bytes = selfie_image_file.read()

    response = rekognition_client.compare_faces(
        SourceImage={
            'Bytes': cnh_image_bytes
        },
        TargetImage={
            'Bytes': selfie_image_bytes
        },
        SimilarityThreshold=60
    )

    if 'FaceMatches' in response and response['FaceMatches']:
        similarity = response['FaceMatches'][0]['Similarity']
        return similarity
    else:
        return 0

@app.route('/', methods=['GET', 'POST'])
def index():
    extracted_text = None
    similarity = None

    if request.method == 'POST':
        if 'cnh_image' not in request.files or 'selfie_image' not in request.files:
            return "No file part"

        cnh_image = request.files['cnh_image']
        selfie_image = request.files['selfie_image']

        if cnh_image.filename == '' or selfie_image.filename == '':
            return "No selected file"

        cnh_image.save("temp_cnh.png")
        selfie_image.save("temp_selfie.png")

        extracted_text = extract_text_from_image("temp_cnh.png")
        similarity = compare_faces("temp_cnh.png", "temp_selfie.png")

        os.remove("temp_cnh.png")
        os.remove("temp_selfie.png")

    return render_template('index.html', extracted_text=extracted_text, similarity=similarity)

if __name__ == "__main__":
    app.run(debug=True)


