# install_deps.py
import subprocess
import torch

def install_requirements():
    try:
        if torch.cuda.is_available():
            print("GPU detected: Installing CUDA-enabled torch...")
            subprocess.run([
                "pip", "install",
                "torch==2.3.0+cu118",
                "-f", "https://download.pytorch.org/whl/torch_stable.html"
            ], check=True)
        else:
            print("No GPU detected: Installing CPU-only torch...")
            subprocess.run(["pip", "install", "torch"], check=True)

        with open("requirements.txt", "r") as file:
            lines = file.readlines()

        filtered_lines = [line.strip() for line in lines if not line.strip().startswith("-e")]

        with open("temp_requirements.txt", "w") as temp_file:
            temp_file.write("\n".join(filtered_lines))

        subprocess.run(["pip", "install", "-r", "temp_requirements.txt"], check=True)

    except subprocess.CalledProcessError as e:
        print(f"Installation failed: {e}")

if __name__ == "__main__":
    install_requirements()
