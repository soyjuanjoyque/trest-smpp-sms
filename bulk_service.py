from fastapi import APIRouter, HTTPException
import requests
import asyncio
import aiohttp

router = APIRouter()

SEND_MESSAGE_URL = "http://localhost:8000/sendMessage"

async def send_message_async(session, message):
    xml_message = f"""<?xml version="1.0"?>
        <AoSmsRequest>
            <AoSms>
                <aAddress>{message['aAddress']}</aAddress>
                <bAddress>{message['bAddress']}</bAddress>
                <Message>{message['Message']}</Message>
                <DataCodingScheme>{message.get('DataCodingScheme', 0)}</DataCodingScheme>
            </AoSms>
        </AoSmsRequest>"""

    try:
        async with session.post(SEND_MESSAGE_URL, data=xml_message, headers={"Content-Type": "application/xml"}, timeout=20) as response:
            if response.status != 200:
                return {"bAddress": message['bAddress'], "status": "failed", "response": await response.text()}
            else:
                return {"bAddress": message['bAddress'], "status": "success", "response": await response.text()}

    except Exception as e:
        return {"bAddress": message['bAddress'], "status": "failed", "response": str(e)}

@router.post("/bulkSend")
async def bulk_send(payload: dict):
    b_addresses = payload.get("bAddresses", [])
    a_address = payload.get("aAddress", "")
    message = payload.get("Message", "")
    data_coding = payload.get("DataCodingScheme", 0)

    if not b_addresses or not message:
        raise HTTPException(status_code=400, detail="Missing bAddresses or Message in the request.")

    async with aiohttp.ClientSession() as session:
        tasks = []
        for bAddress in b_addresses:
            tasks.append(send_message_async(session, {
                "aAddress": a_address,
                "bAddress": bAddress,
                "Message": message,
                "DataCodingScheme": data_coding
            }))
        results = await asyncio.gather(*tasks)

    return {"results": results}
