import httpx
import sys
import os

def test_upload(file_path):
    url = "http://localhost:8000/api/v1/files/upload"
    
    if not os.path.exists(file_path):
        # Create a dummy file if not provided/exists
        with open("test_file.txt", "w") as f:
            f.write("This is a test file for upload endpoint.")
        file_path = "test_file.txt"
        print(f"Created dummy file: {file_path}")

    files = {'file': open(file_path, 'rb')}
    try:
        print(f"Uploading {file_path} to {url}...")
        response = httpx.post(url, files=files)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        files['file'].close()
        # Clean up if we created the file
        if file_path == "test_file.txt" and os.path.exists(file_path):
             os.remove(file_path)

if __name__ == "__main__":
    file_path = sys.argv[1] if len(sys.argv) > 1 else "test_file.txt"
    test_upload(file_path)
