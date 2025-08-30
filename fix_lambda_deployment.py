#!/usr/bin/env python3
"""
Fix Lambda deployment by creating proper deployment package
This script keeps the existing lambda_function.py unchanged
"""

import os
import shutil
import zipfile
import subprocess
import sys
import tempfile
from pathlib import Path

def fix_lambda_deployment():
    """Fix the Lambda deployment package structure"""
    
    # Get current directory
    current_dir = Path.cwd()
    lambda_function_path = current_dir / "lambda_function.py"
    
    if not lambda_function_path.exists():
        print("❌ Error: lambda_function.py not found in current directory")
        return False
    
    print("🔧 Fixing Lambda deployment package...")
    
    # Create temporary directory for building the package
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        package_dir = temp_path / "lambda_package"
        package_dir.mkdir()
        
        print(f"📁 Working in temporary directory: {package_dir}")
        
        # Copy lambda_function.py to package directory
        shutil.copy2(lambda_function_path, package_dir / "lambda_function.py")
        print("✅ Copied lambda_function.py")
        
        # Install dependencies if requirements.txt exists
        requirements_path = current_dir / "requirements.txt"
        if requirements_path.exists():
            print("📦 Installing Python dependencies...")
            try:
                subprocess.run([
                    sys.executable, "-m", "pip", "install",
                    "-r", str(requirements_path),
                    "-t", str(package_dir),
                    "--no-deps"  # Only install direct dependencies to avoid conflicts
                ], check=True, capture_output=True, text=True)
                print("✅ Dependencies installed")
            except subprocess.CalledProcessError as e:
                print(f"⚠️ Warning: Error installing dependencies: {e}")
                print("Continuing without additional dependencies...")
        
        # Create the zip file
        zip_path = current_dir / "lambda_function_fixed.zip"
        
        print(f"📦 Creating deployment package: {zip_path}")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(package_dir):
                for file in files:
                    file_path = Path(root) / file
                    # Calculate relative path from package directory
                    arcname = file_path.relative_to(package_dir)
                    zipf.write(file_path, arcname)
                    print(f"  Added: {arcname}")
        
        print(f"✅ Created deployment package: {zip_path}")
        
        # Verify the zip structure
        print("\n📋 Verifying package structure:")
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            for name in zipf.namelist()[:10]:  # Show first 10 files
                print(f"  {name}")
            if len(zipf.namelist()) > 10:
                print(f"  ... and {len(zipf.namelist()) - 10} more files")
        
        return True

def get_lambda_function_name():
    """Try to detect the Lambda function name from deployment files"""
    
    current_dir = Path.cwd()
    
    # Look for deployment scripts
    deploy_files = [
        "deploy_phi2_lambda.py",
        "auto_deploy.py",
        "deploy_phi2_v5.py"
    ]
    
    for deploy_file in deploy_files:
        deploy_path = current_dir / deploy_file
        if deploy_path.exists():
            try:
                with open(deploy_path, 'r') as f:
                    content = f.read()
                    # Look for function name patterns
                    if "function_name" in content.lower():
                        print(f"📄 Found deployment file: {deploy_file}")
                        return None  # Let user check manually
            except:
                continue
    
    return None

def show_deployment_instructions():
    """Show instructions for deploying the fixed package"""
    
    print("\n" + "="*60)
    print("🚀 DEPLOYMENT INSTRUCTIONS")
    print("="*60)
    
    print("\n1️⃣ Upload the fixed package to Lambda:")
    print("   • Go to AWS Lambda Console")
    print("   • Open your Lambda function")
    print("   • Click 'Upload from' > '.zip file'")
    print("   • Select 'lambda_function_fixed.zip'")
    print("   • Click 'Save'")
    
    print("\n2️⃣ Or use AWS CLI:")
    print("   aws lambda update-function-code \\")
    print("     --function-name YOUR_FUNCTION_NAME \\")
    print("     --zip-file fileb://lambda_function_fixed.zip")
    
    print("\n3️⃣ Verify the handler is set correctly:")
    print("   • Handler should be: lambda_function.lambda_handler")
    print("   • Runtime should be: python3.9 or python3.11")
    
    print("\n4️⃣ Test the function:")
    print("   • Use the test event in Lambda console")
    print("   • Or run your test_function_url.py script")
    
    print("\n✅ The lambda_function.py file remains unchanged!")

def main():
    """Main function"""
    
    print("🔧 Lambda Deployment Fix Tool")
    print("=" * 40)
    
    if fix_lambda_deployment():
        show_deployment_instructions()
        print("\n🎉 Package fixed successfully!")
        print("   File created: lambda_function_fixed.zip")
    else:
        print("\n❌ Failed to fix deployment package")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
