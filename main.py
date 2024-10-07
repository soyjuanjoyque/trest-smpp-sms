from fastapi import FastAPI, HTTPException, Request, Response
import xmltodict
from smpp_service_test import connect_to_smpp, send_smpp_message, disconnect_from_smpp
from dotenv import load_dotenv
from pymongo import MongoClient
import os
from bulk_service import router as bulk_router

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db_name = os.getenv("MONGO_DB_NAME")
collection_name = os.getenv("MONGO_COLLECTION_NAME")
db = client[db_name]
collection = db[collection_name]

SMPP_SERVER = os.getenv("SMPP_SERVER")
SMPP_PORT = int(os.getenv("SMPP_PORT"))
SMPP_SYSTEM_ID = os.getenv("SMPP_SYSTEM_ID")
SMPP_PASSWORD = os.getenv("SMPP_PASSWORD")

app = FastAPI()

app.include_router(bulk_router)

def validate_address(address):
    return address.isalnum()

@app.post("/sendMessage", response_class=Response)
async def send_message(request: Request):
    try:
        request_body = await request.body()

        data = xmltodict.parse(request_body)

        ao_sms = data['AoSmsRequest']['AoSms']
        aAddress = ao_sms.get('aAddress', SMPP_SYSTEM_ID)
        bAddress = ao_sms['bAddress']
        message = ao_sms['Message']
        data_coding = int(ao_sms.get('DataCodingScheme', 0))

        if not validate_address(aAddress):
            return Response(
                content=xmltodict.unparse({
                    "AoSmsResponse": {
                        "Code": "1",
                        "Description": "Invalid aAddress",
                        "ResultList": {
                            "Result": {
                                "MessageId": None,
                                "Status": "3",
                                "Description": "Invalid Address"
                            }
                        }
                    }
                }, pretty=True), media_type="application/xml")
        if not validate_address(bAddress):
            return Response(
                content=xmltodict.unparse({
                    "AoSmsResponse": {
                        "Code": "1",
                        "Description": "Invalid bAddress",
                        "ResultList": {
                            "Result": {
                                "MessageId": None,
                                "Status": "3",
                                "Description": "Invalid Address"
                            }
                        }
                    }
                }, pretty=True), media_type="application/xml")

        client = connect_to_smpp(SMPP_SERVER, SMPP_PORT, SMPP_SYSTEM_ID, SMPP_PASSWORD)
        result = send_smpp_message(client, aAddress, bAddress, message)
        disconnect_from_smpp(client)

        message_id = result['message_id']
        description = "Message sent successfully"

        mensaje_guardado = {
            "MessageId": message_id,
            "aAddress": aAddress,
            "bAddress": bAddress,
            "Message": message,
            "DataCodingScheme": data_coding,
            "Status": "0",
            "Description": description
        }
        collection.insert_one(mensaje_guardado)

        response_dict = {
            "AoSmsResponse": {
                "Code": "0",
                "Description": "No Error",
                "ResultList": {
                    "Result": {
                        "MessageId": message_id,
                        "Status": "0",
                        "Description": description
                    }
                }
            }
        }

        xml_response = xmltodict.unparse(response_dict, pretty=True)
        return Response(content=xml_response, media_type="application/xml")

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/queryMessage", response_class=Response)
async def query_message(message_id: int):
    try:
        mensaje = collection.find_one({"MessageId": message_id})

        if not mensaje:
            return Response(
                content=xmltodict.unparse({
                    "AoSmsResponse": {
                        "Code": "1",
                        "Description": "Message not found",
                        "ResultList": {
                            "Result": {
                                "MessageId": None,
                                "Status": "1",
                                "Description": "Message ID not found"
                            }
                        }
                    }
                }, pretty=True), media_type="application/xml")

        response_dict = {
            "AoSmsResponse": {
                "Code": "0",
                "Description": "No Error",
                "ResultList": {
                    "Result": {
                        "MessageId": mensaje["MessageId"],
                        "Status": mensaje["Status"],
                        "Description": mensaje["Description"]
                    }
                }
            }
        }

        xml_response = xmltodict.unparse(response_dict, pretty=True)
        return Response(content=xml_response, media_type="application/xml")

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/cancelMessage", response_class=Response)
async def cancel_message(request: Request):
    try:
        request_body = await request.body()
        data = xmltodict.parse(request_body)
        
        message_id = data['AoSmcancelRequest']['AoSmcancel'].get('MessageId')
        aAddress = data['AoSmcancelRequest']['AoSmcancel'].get('aAddress')

        if not message_id or not aAddress:
            return Response(
                content=xmltodict.unparse({
                    "AoSmcancelResponse": {
                        "Code": "1",
                        "Description": "Faltan MessageId o aAddress",
                        "ResultList": {
                            "Result": {
                                "Status": "1",
                                "Description": "Solicitud inválida, se requieren tanto MessageId como aAddress"
                            }
                        }
                    }
                }, pretty=True), media_type="application/xml")
        
        mensaje = collection.find_one({"MessageId": int(message_id)})

        if not mensaje:
            return Response(
                content=xmltodict.unparse({
                    "AoSmcancelResponse": {
                        "Code": "1",
                        "Description": "Mensaje no encontrado",
                        "ResultList": {
                            "Result": {
                                "Status": "1",
                                "Description": "Message ID no encontrado"
                            }
                        }
                    }
                }, pretty=True), media_type="application/xml")

        collection.update_one({"MessageId": int(message_id)}, {"$set": {"Status": "Cancelado", "Description": "Mensaje cancelado"}})

        response_dict = {
            "AoSmcancelResponse": {
                "Code": "0",
                "Description": "No Error",
                "ResultList": {
                    "Result": {
                        "Status": "0",
                        "Description": "Mensaje cancelado exitosamente"
                    }
                }
            }
        }

        xml_response = xmltodict.unparse(response_dict, pretty=True)
        return Response(content=xml_response, media_type="application/xml")

    except Exception as e:
        return Response(
            content=xmltodict.unparse({
                "AoSmcancelResponse": {
                    "Code": "1",
                    "Description": str(e),
                    "ResultList": {
                        "Result": {
                            "Status": "1",
                            "Description": "Ocurrió un error durante la cancelación"
                        }
                    }
                }
            }, pretty=True), media_type="application/xml")
