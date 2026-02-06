# ====================================================================================================================
# This program was modified by Darryl LeCraw [n01712877]
# ====================================================================================================================

import socket
import argparse
import struct
import os
import hashlib

def compute_checksum(data):
     # MAKE A 16-BIT INTERNET CHECKSUM (RFC 1071)
    if len(data) % 2 == 1:
        data += b'\x00'
    total = 0
    for i in range(0, len(data), 2):
        word = (data[i] << 8) + data[i + 1]
        total += word
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return ~total & 0xFFFF


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
            checksum_pass = 0
            checksum_fail = 0

            while True:
                data, addr = serv_sock.recvfrom(4096)

                # CHECK FOR EOF: PACKET WITH 'EOF' MARKER AFTER SEQ HEADER
                # FORMAT: [4B SEQ][3B 'EOF'][32B MD5 HEX] = 39 BYTES
                if len(data) >= 7 and data[4:7] == b'EOF':
                    eof_seq = struct.unpack('!I', data[:4])[0]
                    serv_sock.sendto(struct.pack('!I', eof_seq), addr)
                    print(f"[*] CLOSING AFTER END OF FILE SIGNAL RECEIVED FROM ADDR[{addr}]")

                    # EXTRACT CLIENT MD5 FROM EOF PACKET
                    if len(data) >= 39:
                        client_md5 = data[7:39].decode('utf-8')
                    else:
                        client_md5 = None

                    # FLUSH ANY REMAINING BUFFERED PACKETS
                    while expected_seq in buffer:
                        if f:
                            f.write(buffer.pop(expected_seq))
                            expected_seq += 1

                    break

                # UNPACK SEQUENCE NUMBER, CHECKSUM, AND PAYLOAD
                seq_num = struct.unpack('!I', data[:4])[0]
                recv_checksum = struct.unpack('!H', data[4:6])[0]
                payload = data[6:]

                # VERIFY PER-PACKET CHECKSUM
                calc_checksum = compute_checksum(payload)
                if recv_checksum == calc_checksum:
                    checksum_pass += 1
                else:
                    checksum_fail += 1
                    print(f"[!] CHECKSUM MISMATCH ON SEQ({seq_num})! RECV({recv_checksum:#06x}) CALC({calc_checksum:#06x})")

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

            # PRINT PER-PACKET CHECKSUM SUMMARY
            total_packets = checksum_pass + checksum_fail
            print(f"[*] PACKET CHECKSUM SUMMARY: {checksum_pass}/{total_packets} PASSED, {checksum_fail}/{total_packets} FAILED")

            if f:
                f.close()

            # UDP FINAL CHECK: COMPUTE MD5 OF RECEIVED FILE AND COMPARE WITH CLIENT
            if sender_filename and os.path.exists(sender_filename):
                server_md5 = hashlib.md5(open(sender_filename, 'rb').read()).hexdigest()

                if client_md5:
                    print(f"[*] UDP FINAL CHECK - CLIENT MD5[{client_md5}]")
                    print(f"[*] UDP FINAL CHECK - SERVER MD5[{server_md5}]")
                    if client_md5 == server_md5:
                        print("[*] UDP FINAL CHECK - MATCH! FILE INTEGRITY VERIFIED!")
                    else:
                        print("[!] UDP FINAL CHECK - MISMATCH! FILE MAY BE CORRUPTED!")
                else:
                    print(f"[*] UDP FINAL CHECK - SERVER MD5[{server_md5}]")
                    print("[!] UDP FINAL CHECK - NO CLIENT CHECKSUM RECEIVED FOR COMPARISON")

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
