	
import sys
sys.path.insert(0, 'src/vendor')

import json
import io
import cgi
import base64
import os
import shutil
import boto3
import pathlib
import uuid
from datetime import datetime
from kiotviet_format import kiotviet_format


def format(event, context):
    fp = io.BytesIO(base64.b64decode(event['body']))

    fs = cgi.FieldStorage(fp=fp, environ={"REQUEST_METHOD": "POST"}, headers={
        "content-type": event["headers"]["content-type"],
        "content-length": event['headers']["content-length"],
    })

    id = str(uuid.uuid4())
    workdir = f"/tmp/{id}"
    input_dir = f"{workdir}/input"
    output_dir = f"{workdir}/output"

    pathlib.Path(workdir).mkdir(exist_ok=True)

    zipInput = open(f"{workdir}/input.zip", "wb")
    zipInput.write(fs.getvalue("file"))

    shutil.unpack_archive(f"{workdir}/input.zip", f"{input_dir}")
    pathlib.Path(output_dir).mkdir(exist_ok=True)
    kiotviet_format.format_files(input_dir, output_dir)

    shutil.make_archive(f'{workdir}/result', format='zip', root_dir=output_dir)

    session = boto3.Session(
        aws_access_key_id=os.environ['ACCESS_KEY_ID'],
        aws_secret_access_key=os.environ['SECRET_ACCESS_KEY'],
    )

    s3 = session.resource("s3")
    bucket = s3.Bucket("tuan-test")
    date = datetime.now().date()
    bucket.upload_file(f"{workdir}/result.zip", f"{str(date)}.zip")
    response = {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "url": session.client('s3').generate_presigned_url('get_object', Params={'Bucket': "tuan-test", 'Key': f"{str(date)}.zip"}, ExpiresIn=3600)
        })
    }

    return response
