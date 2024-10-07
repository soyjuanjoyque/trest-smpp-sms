import random

def connect_to_smpp(server_ip, server_port, system_id, password):
    print(f"Conectado al servidor SMPP simulado en {server_ip}:{server_port}")
    return True

def send_smpp_message(client, source_addr, destination_addr, short_message):
    print(f"Simulando envío de mensaje: {short_message} desde {source_addr} a {destination_addr}")
    message_id = random.randint(1000, 9999)
    return {"message_id": message_id, "status": "Message sent successfully (Simulado)"}

def disconnect_from_smpp(client):
    print("Simulación de desconexión del servidor SMPP")
    return True

def query_message_status(message_id):
    message_state = random.choice(["DELIVERED", "PENDING", "FAILED"])
    return {"message_id": message_id, "status": message_state}

def cancel_smpp_message(message_id):
    print(f"Simulando cancelación de mensaje con ID: {message_id}")
    return {"message_id": message_id, "status": "Message cancelled (Simulado)"}
