
def createPacket(num_seq, data=b''):
    seq_bytes = num_seq.to_bytes(4, byteorder='little', signed=True)
    return seq_bytes + data


def createEmptyPacket():
    return b''


def extractPacket(packet):
    num_seq = int.from_bytes(packet[0:4], byteorder='little', signed=True)
    return num_seq, packet[4:]
