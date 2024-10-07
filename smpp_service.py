import smpplib.client
import smpplib.consts
import smpplib.gsm


def connect_to_smpp(server_ip, server_port, system_id, password):
    client = smpplib.client.Client(server_ip, server_port)
    client.connect()
    client.bind_transmitter(system_id=system_id, password=password)
    return client

def send_smpp_message(client, source_addr, destination_addr, short_message):
    pdu = client.send_message(
        source_addr_ton=smpplib.consts.SMPP_TON_INTL,
        source_addr=source_addr,
        dest_addr_ton=smpplib.consts.SMPP_TON_INTL,
        destination_addr=destination_addr,
        short_message=smpplib.gsm.make_parts(short_message)
    )
    return {"message_id": pdu.message_id, "status": "Message sent successfully"}

def disconnect_from_smpp(client):
    client.unbind()
    client.disconnect()
