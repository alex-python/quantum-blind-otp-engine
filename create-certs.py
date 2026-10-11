import os
import subprocess

def create_mtls_certs_from_scratch(target_dir="ssl_context"):
    """
    Programmatically builds a complete mTLS PKI deployment from scratch.
    Injects mandatory Subject Alternative Names (SAN) for local loopback verification.
    """
    # 1. Create target directory architecture if not already present
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
        print(f"📁 Created directory: '{target_dir}'")
        
    print("🔐 Starting OpenSSL generation pipeline...")

    # 2. Define the explicit SAN configuration parameters inline
    san_config_content = """
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
x509_extensions = v3_req
prompt = no

[req_distinguished_name]
CN = 127.0.0.1

[v3_req]
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
IP.1 = 127.0.0.1
DNS.1 = localhost
"""
    config_path = os.path.join(target_dir, "san_ext.cnf")
    with open(config_path, "w") as f:
        f.write(san_config_content.strip())

    try:
        # Step A: Generate Private Root Certificate Authority (CA)
        print("   -> Spawning local Root CA...")
        subprocess.run(
            f'openssl req -x509 -newkey rsa:4096 -days 365 -nodes '
            f'-keyout {target_dir}/ca.key -out {target_dir}/ca.crt '
            f'-subj "/CN=LocalChaosCA"', 
            shell=True, check=True, capture_output=True
        )

        # Step B: Generate Server Private Key & Certificate Signing Request (CSR) with SAN config
        print("   -> Spawning Server CSR with SAN maps...")
        subprocess.run(
            f'openssl req -new -newkey rsa:2048 -nodes '
            f'-keyout {target_dir}/server.key -out {target_dir}/server.csr '
            f'-config {config_path}', 
            shell=True, check=True, capture_output=True
        )

        # Step C: Sign the Server CSR using the Root CA, enforcing v3_req extensions containing SAN
        print("   -> Signing Server Certificate via Root CA...")
        subprocess.run(
            f'openssl x509 -req -in {target_dir}/server.csr '
            f'-CA {target_dir}/ca.crt -CAkey {target_dir}/ca.key -CAcreateserial '
            f'-days 365 -out {target_dir}/server.crt '
            f'-extfile {config_path} -extensions v3_req', 
            shell=True, check=True, capture_output=True
        )

        # Step D: Generate Client Private Key & CSR
        print("   -> Spawning Client identity keys...")
        subprocess.run(
            f'openssl req -new -newkey rsa:2048 -nodes '
            f'-keyout {target_dir}/client.key -out {target_dir}/client.csr '
            f'-subj "/CN=SecureClient"', 
            shell=True, check=True, capture_output=True
        )

        # Step E: Sign Client Certificate via Root CA
        print("   -> Signing Client Certificate...")
        subprocess.run(
            f'openssl x509 -req -in {target_dir}/client.csr '
            f'-CA {target_dir}/ca.crt -CAkey {target_dir}/ca.key -CAcreateserial '
            f'-days 365 -out {target_dir}/client.crt', 
            shell=True, check=True, capture_output=True
        )

        # Clean up temporary serialization artefacts
        if os.path.exists("ca.srl"):
            os.remove("ca.srl")
            
        print("\n================ PKI DEPLOYMENT SUCCESS ================")
        print(f"✅ All certificates compiled flawlessly inside active folder structure.")
        print(f"📍 Target Output: ./{target_dir}/")
        print("========================================================")

    except subprocess.CalledProcessError as e:
        print(f"\n❌ OpenSSL Pipeline Error: {e.stderr.decode('utf-8')}")
        print("Verify that 'openssl' is installed and active in your system system path.")

if __name__ == "__main__":
    create_mtls_certs_from_scratch()

