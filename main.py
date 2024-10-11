from fastapi import FastAPI, Request, Response, HTTPException
import xmltodict
from pymongo import MongoClient
import os
import base64
import logging
from dotenv import load_dotenv
import httpx
import asyncio

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = MongoClient(MONGO_URI)
db = client[os.getenv("MONGO_DB_NAME")]
collection = db[os.getenv("MONGO_COLLECTION_NAME")]

REST_SERVER_BASE_URL = os.getenv("REST_SERVER_BASE_URL")
AUTHORIZATION_HEADER = os.getenv("AUTHORIZATION_HEADER")
CONTENT_TYPE = os.getenv("CONTENT_TYPE")

app = FastAPI()

logging.basicConfig(level=logging.INFO)

async def send_request(xml_body: str, endpoint: str):
    try:
        url = f"{REST_SERVER_BASE_URL}/{endpoint}"
        headers = {
            'Authorization': AUTHORIZATION_HEADER,
            'Content-Type': CONTENT_TYPE
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, data=xml_body)
        logging.info(f"Request sent to {url}, received status: {response.status_code}")
        response.raise_for_status()
        return response.text
    except httpx.RequestError as e:
        logging.error(f"Request failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")

def encode_message_in_base64(xml_body: str) -> str:
    xml_dict = xmltodict.parse(xml_body)
    
    message = xml_dict['AoSmsRequest']['AoSms'].get('Message')
    if message:
        encoded_message = base64.b64encode(message.encode('utf-8')).decode('utf-8')
        xml_dict['AoSmsRequest']['AoSms']['Message'] = encoded_message

    return xmltodict.unparse(xml_dict, pretty=True)

@app.post("/send_message")
async def send_message(request: Request):
    try:
        xml_body = await request.body()
        
        xml_body_encoded = encode_message_in_base64(xml_body.decode('utf-8'))

        response = await send_request(xml_body.decode('utf-8'), "AoSms")
        
        log_entry = {
            "xml_body": xml_body.decode('utf-8'),
            "xml_body_encoded": xml_body_encoded,
            "response": response
        }
        
        collection.insert_one(log_entry)
        
        return Response(content=response, media_type="application/xml")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query_message")
async def query_message(request: Request):
    try:
        xml_body = await request.body()

        response = await send_request(xml_body.decode('utf-8'), "AoSmquery")

        return Response(content=response, media_type="application/xml")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cancel_message")
async def cancel_message(request: Request):
    try:
        xml_body = await request.body()
        data = xmltodict.parse(xml_body)
        message_id = data.get('AoSmcancelRequest', {}).get('AoSmcancel', {}).get('MessageId')
        a_address = data.get('AoSmcancelRequest', {}).get('AoSmcancel', {}).get('aAddress')

        if not message_id or not a_address:
            return Response(
                content=xmltodict.unparse({
                    "AoSmcancelResponse": {
                        "Code": "1",
                        "Description": "Missing MessageId or aAddress",
                        "ResultList": {
                            "Result": {
                                "Status": "1",
                                "Description": "Invalid request, both MessageId and aAddress are required"
                            }
                        }
                    }
                }, pretty=True), media_type="application/xml")

        response = await send_request(xml_body.decode('utf-8'), "AoSmcancel")

        collection.update_one(
            { "response": { "$regex": message_id } },
            { "$set": { "Description": "MESSAGE CANCELLED" } }
        )
        
        return Response(content=response, media_type="application/xml")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def send_message_async(a_address: str, b_address: str, message: str, data_coding_scheme: int):
    try:
        xml_body = f"""
            <AoSmsRequest>
                <AoSms>
                    <aAddress>{a_address}</aAddress>
                    <bAddress>{b_address}</bAddress>
                    <Message>{message}</Message>
                    <DataCodingScheme>{data_coding_scheme}</DataCodingScheme>
                </AoSms>
            </AoSmsRequest>
        """
        xml_body_encoded = encode_message_in_base64(xml_body)
        response = await send_request(xml_body_encoded, "AoSms")

        log_entry = {
            "aAddress": a_address,
            "bAddress": b_address,
            "xml_body": xml_body,
            "xml_body_encoded": xml_body_encoded,
            "response": response
        }

        collection.insert_one(log_entry)

        return {"bAddress": b_address, "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/bulk_send")
async def bulk_send(request: Request):
    try:
        body = await request.json()
        a_address = body['aAddress']
        b_addresses = body['bAddresses']
        message = body['Message']
        data_coding_scheme = body['DataCodingScheme']

        tasks = []

        for b_address in b_addresses:
            tasks.append(send_message_async(a_address, b_address, message, data_coding_scheme))

        results = await asyncio.gather(*tasks)

        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))