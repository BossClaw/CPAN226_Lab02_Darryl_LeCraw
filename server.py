# ====================================================================================================================
# This program was modified by Darryl LeCraw [n01712877]
# ====================================================================================================================

import socket
import argparse
import struct
import os

def run_server(port, output_file):
    # CREATE UDP SOCKET
    serv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # BIND TO ALL INTERFACES ON THE GIVEN PORT
    server_address = ('', port)
    print(f"[*] SERVER LISTENING ON PORT[{port}]")
    print(f"[*] SERVER WILL SAVE RECEIVED FILES BASED ON['{output_file}'] WITH SENDER ADDR SUFFIX")
    serv_sock.bind(server_address)

    # KEEP LISTENING FOR NEW TRANSFERS
    try:
        while True:
            f = None
            sender_filename = None
            expected_seq = 0
            buffer = {}

            while True:
                data, addr = serv_sock.recvfrom(4096)

                # CHECK FOR EOF: PACKET WITH ONLY 4-BYTE HEADER (NO PAYLOAD)
                if len(data) <= 4:
                    # SEND EOF ACK
                    eof_seq = struct.unpack('!I', data[:4])[0] if len(data) == 4 else expected_seq
                    serv_sock.sendto(struct.pack('!I', eof_seq), addr)
                    print(f"[*] CLOSING AFTER END OF FILE SIGNAL RECEIVED FROM ADDR[{addr}]")

                    # FLUSH ANY REMAINING BUFFERED PACKETS
                    while expected_seq in buffer:
                        if f:
                            f.write(buffer.pop(expected_seq))
                            expected_seq += 1

                    break

                # UNPACK SEQUENCE NUMBER AND PAYLOAD
                seq_num = struct.unpack('!I', data[:4])[0]
                payload = data[4:]

                # OPEN FILE ON FIRST PACKET
                if f is None:
                    print("==== START OF RECEPTION ====")
                    ip, sender_port = addr
                    name, ext = os.path.splitext(output_file)
                    sender_filename = f"{name}_{ip.replace('.', '_')}_{sender_port}{ext}"
                    f = open(sender_filename, 'wb')
                    print(f"[*] FIRST PACKET RECEIVED FROM ADDR[{addr}]. FILE OPENED FOR WRITING AS['{sender_filename}']")

                # ALWAYS ACK THE RECEIVED SEQ NUM
                serv_sock.sendto(struct.pack('!I', seq_num), addr)

                # REORDER LOGIC
                if seq_num == expected_seq:
                    # IN-ORDER: WRITE AND FLUSH CONSECUTIVE BUFFERED PACKETS
                    f.write(payload)
                    expected_seq += 1

                    while expected_seq in buffer:
                        f.write(buffer.pop(expected_seq))
                        expected_seq += 1

                elif seq_num > expected_seq:
                    # FUTURE PACKET: BUFFER FOR LATER
                    buffer[seq_num] = payload
                # seq_num < expected_seq: DUPLICATE, IGNORE

            if f:
                f.close()
            print("==== END OF RECEPTION ====")

    except KeyboardInterrupt:
        print("\n[!] NOTICE!! SERVER STOPPED MANUALLY. ( why would you do such a thing? )")
    except Exception as e:
        print(f"[!] EXCEPTION ERROR!!! [{e}]")
    finally:
        serv_sock.close()
        print("[*] SERVER SOCKET CLOSED")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reliable UDP File Receiver (Stop-and-Wait)")
    parser.add_argument("--port", type=int, default=12001, help="Port to listen on")
    parser.add_argument("--output", type=str, default="received_file.jpg", help="File path to save data")
    args = parser.parse_args()

    try:
        run_server(args.port, args.output)
    except KeyboardInterrupt:
        print("\n[!] SERVER STOPPED MANUALLY")
    except Exception as e:
        print(f"[!] EXEPTION ERROR[{e}]")
