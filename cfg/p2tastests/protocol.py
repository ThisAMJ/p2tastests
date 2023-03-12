import socket
import struct
import time

inPath = "instruction.log"
outPath = "proto-output.cfg"

with open(outPath, "w") as f: f.write("")
with open(inPath, "w") as f: f.write("")

# Connect as a TAS client
HOST = "127.0.0.1"
PORT = 6555
sock = socket.socket()
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

gamedir = "unknown"

def output(message: any):
	with open(outPath, "r") as f: 
		lines = f.read().rstrip().split('\n')
		if (len(lines) > 1): lines.pop()
		with open(outPath, "w") as f: f.write('\n'.join(lines) + '\n' + message + "\n__proto_clearout\n")

print("Waiting for message from p2tastests...")
while True:
	with open(inPath, "r") as f:
		lines = f.read().rstrip().split('\n')
		if (len(lines) > 0 and lines[len(lines) - 1] == "connect"):
			with open(inPath, "w") as f: f.write("")
			try: sock.connect((HOST, PORT))
			except: 
				print("Connection failure. Close the game, wait a minute, then try again.")
				output("test_pure_fail proto-conn")
				continue
			sock.setblocking(False)
			print("Connected successfully!")
			output("test_pure_succeed proto-conn")
			break

# Send message to SAR
def send_message(type: str, data: any):
	packet = b''
	more = b''
	typeI = -1
	if (type == "play"):
		typeI = 0
		more = struct.pack("!I", len(data[0]))
		more += data[0].encode()
		string = ""
		if (len(data) == 2):
			more += struct.pack("!I", len(data[1]))
			more += data[1].encode()
			string = " & " + data[1]
		else:
			more += struct.pack("!I", 0) # SP tas
		print("Play - " + data[0] + string)

	if (type == "stop"):
		typeI = 1
		print("Stop")

	if (type == "rate"):
		typeI = 2
		more = struct.pack("!f", float(data))
		print("SetPlaybackRate = " + data)
		output("test_succeed proto-rate")

	if (type == "unpause"):
		typeI = 3
		print("Unpause")

	if (type == "pause"):
		typeI = 4
		print("Pause")

	if (type == "fastforward" or type == "ffwd" or type == "skip" or type == "skipto"):
		typeI = 5
		if len(data) != 2:
			data.append("0")
		more = struct.pack("!I", int(data[0]))
		more += struct.pack("!B", int(data[1]))
		string = ""
		if data[1] == "0": string = "NOT "
		print("SkipTo " + data[0] + ", " + string + "pausing after")

	if (type == "pauseat"):
		typeI = 6
		more += struct.pack("!I", int(data))
		print("SetPauseAtTick = ", data)

	if (type == "advance"):
		typeI = 7
		print("AdvanceTick")

	if (type == "playtxt"):
		typeI = 10
		more = struct.pack("!I", len(data[0]))
		more += data[0].encode()
		more += struct.pack("!I", len(data[1]))
		more += data[1].encode()
		more += struct.pack("!I", len(data[2]))
		more += data[2].encode()
		more += struct.pack("!I", len(data[3]))
		more += data[3].encode()
		print("PlayTextScript")

	if (type == "entity"):
		typeI = 100
		print("EntityRequest - " + data)
		more = struct.pack("!I", len(data))
		more += data.encode()

	if (type == "clearoutput"):
		with open(outPath, "w") as f: f.write("")
		with open(inPath, "w") as f: f.write("")
		return

	if typeI == -1: 
		output("echo ERR: Unknown user message type " + type + "!")
		print("ERR: Unknown user message type \"" + type + "\"!")
		return

	packet += struct.pack("!B", typeI)
	packet += more
	# print("INFO: Send: " + str(packet))
	sock.send(packet)

# Receive message from SAR
def recv_message():
	# Read messages until there is no message to read
	while True:
		try: typeMsg = sock.recv(1)
		except BlockingIOError: return
		if not typeMsg: return
		typeI = struct.unpack("!B", typeMsg)[0]
		type = ""
		if (typeI == 0):
			type = "setactive"
			len1 = struct.unpack("!I", sock.recv(4))[0]
			filename1 = struct.unpack("!"+str(len1)+"s", sock.recv(len1))[0].decode()
			len2 = struct.unpack("!I", sock.recv(4))[0]
			filename2 = ""
			string = ""
			if (len2 != 0):
				filename2 = struct.unpack("!"+str(len2)+"s", sock.recv(len2))[0].decode()
				string = " \"" + filename2 + "\""
			output("test_pure_succeed proto-active")
			print("SetActive - " + filename1 + string)

		if (typeI == 1):
			type = "setinactive"
			output("test_pure_succeed proto-inact")
			print("SetInactive")

		if (typeI == 2):
			type = "speed"
			rate = struct.unpack("!f", sock.recv(4))[0]
			output("test_pure_succeed proto-rate")
			print("PlaybackRate - " + str(rate))

		if (typeI == 3):
			type = "playing"
			output("test_pure_succeed proto-splay")
			print("State = Playing")

		if (typeI == 4):
			type = "paused"
			output("test_pure_succeed proto-spause")
			print("State = Paused")

		if (typeI == 5):
			type = "fastforward"
			output("test_pure_succeed proto-sffwd")
			print("State = FFWD")

		if (typeI == 6):
			type = "currenttick"
			tick = struct.unpack("!I", sock.recv(4))[0]
			output("test_pure_succeed proto-ctick")

		if (typeI == 7):
			type = "debugtick"
			tick = struct.unpack("!i", sock.recv(4))[0]
			output("test_pure_succeed proto-dtick")

		if (typeI == 10):
			type = "processedscript"
			slot = struct.unpack("!B", sock.recv(1))[0]
			lenscript = struct.unpack("!I", sock.recv(4))[0]
			script = struct.unpack("!"+str(lenscript)+"s", sock.recv(lenscript))[0].decode()
			output("test_pure_succeed proto-raw")

		if (typeI == 100):
			type = "entity"
			success = struct.unpack("!B", sock.recv(1))[0]
			if (success == 1):
				position = [
					struct.unpack("!f", sock.recv(4))[0],
					struct.unpack("!f", sock.recv(4))[0],
					struct.unpack("!f", sock.recv(4))[0]
				]
				angles = [
					struct.unpack("!f", sock.recv(4))[0],
					struct.unpack("!f", sock.recv(4))[0],
					struct.unpack("!f", sock.recv(4))[0]
				]
				velocity = [
					struct.unpack("!f", sock.recv(4))[0],
					struct.unpack("!f", sock.recv(4))[0],
					struct.unpack("!f", sock.recv(4))[0]
				]
				output("__proto_ent " + 
					str(position[0]) + ' ' + 
					str(position[1]) + ' ' + 
					str(position[2]) + ' ' + 
					str(angles[0]) + ' ' + 
					str(angles[1]) + ' ' + 
					str(angles[2]) + ' ' + 
					str(velocity[0]) + ' ' + 
					str(velocity[1]) + ' ' + 
					str(velocity[2]))
				print("EntityResponse")
				print("\t" + str(position))
				print("\t" + str(angles))
				print("\t" + str(velocity))

		if (typeI == 255):
			type = "gameloc"
			lenloc = struct.unpack("!I", sock.recv(4))[0]
			gamedir = struct.unpack("!"+str(lenloc)+"s", sock.recv(lenloc))[0].decode()
			output("test_pure_succeed proto-gloc")
			print("GameLocation = " + gamedir)

		if (type == ""):
			output("echo ERR: Unknown SAR message type " + str(typeI) + "!")
			print("ERR: Unknown SAR message type " + str(typeI) + "!")

while True:
	recv_message()
	undo = 0
	done = 0
	type = ""
	data = ""
	do = "0"
	with open(inPath, "r") as f:
		data = f.read()
		lines = data.strip().split('\n')
		
		if (len(lines) > 0):
			if (lines[len(lines) - 1].strip() == "clearoutput"):
				send_message("clearoutput", 0)
				continue
			if (lines[len(lines) - 1].strip() == "connect"):
				with open(inPath, "w") as f: f.write("")
				output("echo ERR: Protocol is already connected. Some protocol tests will falsely fail.\ntest_pure_succeed proto-conn")
				continue

		if (len(lines) > 2):
			type = lines[len(lines) - 3].rstrip(' ')
			data = lines[len(lines) - 2].rstrip(' ')
			do = lines[len(lines) - 1].rstrip(' ')
		if (do == "1"):
			undo = 1
			sData = data
			if (type == "play" or type == "fastforward" or type == "playtxt"): sData = sData.split(",")
			if (type == "playtxt"):
				with open(sData[1], "r") as file:
					sData[1] = file.read()
				if (len(sData) > 2):
					with open(sData[3], "r") as file:
						sData[3] = file.read()
				while len(sData) < 4: sData.append("")
			if (type == "done"):
				done = 1
			else:
				send_message(type, sData)

	# Reset instruction
	if (undo == 1): 
		with open(inPath, "w") as f: f.write("")

	if (done == 1): break
	time.sleep(0.1)

sock.close()
