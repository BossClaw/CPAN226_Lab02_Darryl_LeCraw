# ====================================================================================================================
# This program was modified by Darryl LeCraw [n01712877]
# ====================================================================================================================

import socket
import argparse
import struct
import os

# CONST CHUNK SIZE: 4092 BYTES
# NOTE (4096 - 4 BYTE SEQ HEADER) SO PACKETS FIT RELAY BUFFER
CHUNK_SIZE = 4092
MAX_RETRIES = 50
TIMEOUT = 1.0

def run_client(target_ip, target_port, input_file):
    # CREATE UDP SOCKET
    cli_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    cli_socket.settimeout(TIMEOUT)
    server_address = (target_ip, target_port)

    print(f"[*] SENDING['{input_file}'] TO[{target_ip}:{target_port}]")

    if not os.path.exists(input_file):
        print(f"[!] ERROR! CAN'T FIND['{input_file}']")
        return

    try:
        with open(input_file, 'rb') as f:
            seq_num = 0

            # FOREVER LOOP UNTIL SOMETHING BREAKS IT
            while True:
                # TRY READ NEXT CHUNK
                chunk = f.read(CHUNK_SIZE)

                # IF NOT CHUNK, THEN END OF FILE REACHED, BREAK! 
                if not chunk:
                    break

                # BUILD PACKET: 4-BYTE SEQ HEADER + DATA
                packet = struct.pack('!I', seq_num) + chunk

                # STOP-AND-WAIT: SEND AND WAIT FOR ACK
                retries = 0
                while retries < MAX_RETRIES:
                    cli_socket.sendto(packet, server_address)

                    try:
                        ack_data, _ = cli_socket.recvfrom(4096)
                        ack_num = struct.unpack('!I', ack_data)[0]

                        if ack_num == seq_num:
                            # ACK MATCHES, MOVE TO NEXT CHUNK
                            seq_num += 1
                            break
                    except socket.timeout:
                        retries += 1
                        print(f"[!] TIMEOUT WAITING FOR ACK SEQ_NUM({seq_num}) RETRANSMITTING RETRIES({retries})")
                else:
                    print(f"[!] ERROR! ABORTING AFTER REACHING MAX RETRIES FOR SEQ({seq_num}) RETRIES({retries})")
                    return


        # SEND EOF SIGNAL (EMPTY PACKET WITH SEQ HEADER)
        eof_packet = struct.pack('!I', seq_num)
        retries = 0
        while retries < MAX_RETRIES:
            cli_socket.sendto(eof_packet, server_address)

            try:
                ack_data, _ = cli_socket.recvfrom(4096)
                ack_num = struct.unpack('!I', ack_data)[0]

                if ack_num == seq_num:
                    # EOF ACK RECEIVED
                    break
            except socket.timeout:
                retries += 1
                print(f"[!] TIMEOUT WAITING FOR EOF ACK! RETRANSMITTING RETRIES({retries})")
        else:
            print(f"[!] MAX RETRIES FOR EOF ACK!")

        print(f"[*] FILE TRANSMISSION COMPLETE. CHUNKS/SEQ_NUM({seq_num})")


    except Exception as e:
        print(f"[!] EXCEPTION ERROR!!! [{e}]")
    finally:
        cli_socket.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reliable UDP File Sender (Stop-and-Wait)")
    parser.add_argument("--target_ip", type=str, default="127.0.0.1", help="Destination IP (Relay or Server)")
    parser.add_argument("--target_port", type=int, default=12000, help="Destination Port")
    parser.add_argument("--file", type=str, required=True, help="Path to file to send")
    args = parser.parse_args()

    run_client(args.target_ip, args.target_port, args.file)
