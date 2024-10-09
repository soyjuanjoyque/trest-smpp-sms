from fastapi import FastAPI, Request, Response, HTTPException
import xmltodict
import requests
from pymongo import MongoClient
import os
import httpx
import asyncio
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = MongoClient(MONGO_URI)
db = client[os.getenv("MONGO_DB_NAME", "logDB")]
collection = db[os.getenv("MONGO_COLLECTION_NAME", "requestsLogs")]

REST_SERVER_URL = os.getenv("REST_SERVER_URL")
AUTHORIZATION_HEADER = os.getenv("AUTHORIZATION_HEADER")
CONTENT_TYPE = os.getenv("CONTENT_TYPE")

app = FastAPI()

async def send_message_async(client, xml_body):
    response = await client.post(
        REST_SERVER_URL,
        headers={"Authorization": AUTHORIZATION_HEADER, "Content-Type": CONTENT_TYPE},
        content=xml_body
    )
    
    collection.insert_one({
        "xml_body": xml_body.decode('utf-8'),
        "response_status_code": response.status_code,
        "response_text": response.text
    })
    
    return response.text

@app.post("/send_message")
async def send_message(request: Request):
    xml_body = await request.body()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            REST_SERVER_URL,
            headers={"Authorization": AUTHORIZATION_HEADER, "Content-Type": CONTENT_TYPE},
            content=xml_body
        )
    collection.insert_one({
        "xml_body": xml_body.decode('utf-8'),
        "response_status_code": response.status_code,
        "response_text": response.text
    })
    return Response(content=response.content, media_type="application/xml")

@app.post("/query_message")
async def query_message(request: Request):
    xml_body = await request.body()
    response = requests.post(
        REST_SERVER_URL,
        headers={"Authorization": AUTHORIZATION_HEADER, "Content-Type": CONTENT_TYPE},
        data=xml_body
    )
    return Response(content=response.content, media_type="application/xml")

@app.post("/cancel_message")
async def cancel_message(request: Request):
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

    response = requests.post(
        REST_SERVER_URL,
        headers={"Authorization": AUTHORIZATION_HEADER, "Content-Type": CONTENT_TYPE},
        data=xml_body
    )
    collection.update_one({"MessageId": int(message_id)}, {"$set": {"Status": "Cancelled", "Description": "Message cancelled"}})
    return Response(content=response.content, media_type="application/xml")

@app.post("/bulk_send")
async def bulk_send(request: Request):
    try:
        body = await request.json()
        a_address = body['aAddress']
        b_addresses = body['bAddresses']
        message = body['Message']
        data_coding_scheme = body['DataCodingScheme']

        async with httpx.AsyncClient() as client:
            tasks = []
            for b_address in b_addresses:
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
                tasks.append(send_message_async(client, xml_body.encode('utf-8')))

            results = await asyncio.gather(*tasks)

        return {"results": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))