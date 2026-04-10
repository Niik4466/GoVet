import subprocess

def run_in_backend(script_path):
    """Ejecuta un script de python dentro del contenedor de backend."""
    command = f"docker exec govet-backend-1 python {script_path}"
    print(f"Ejecutando en backend: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error ejecutando script: {result.stderr}")
    return result.returncode == 0, result.stdout
