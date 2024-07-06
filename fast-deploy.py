import subprocess
import time
from ruamel.yaml import YAML

# Set the destination branch here
destination_branch = "mongo"

def run_command(command):
    try:
        print(f"Running command: {command}")
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        print(result.stdout)
        if result.returncode != 0:
            print(result.stderr)
            raise Exception(f"Command failed: {command}")
        return result.stdout.strip()
    except Exception as e:
        print(f"An error occurred while running the command: {e}")
        return None

def wait_for_pods_removal(namespace):
    while True:
        pods = run_command(f"kubectl get pods -n {namespace}")
        if pods is None:
            print("Failed to retrieve pods. Exiting.")
            return False
        
        pod_lines = pods.splitlines()
        if len(pod_lines) <= 1:
            print("No pods found in namespace.")
            break
        
        all_terminating = True
        for line in pod_lines[1:]:
            if "Terminating" not in line:
                all_terminating = False
                break
        
        if all_terminating:
            print("All pods are terminating.")
            break
        
        print("Waiting for pods to terminate...")
        time.sleep(5)
    
    while True:
        pods = run_command(f"kubectl get pods -n {namespace}")
        if pods is None:
            print("Failed to retrieve pods. Exiting.")
            return False
        
        pod_lines = pods.splitlines()
        if len(pod_lines) <= 1:
            print("All pods have been removed.")
            break
        
        print("Waiting for all pods to be removed...")
        time.sleep(5)
    
    return True

def cleanup_test_app():
    # Step 1: Look for test-app chart deployment in test-app namespace
    deployments = run_command("helm ls -n test-app")
    if deployments is None:
        print("Failed to retrieve Helm deployments. Exiting.")
        return

    lines = deployments.splitlines()
    if len(lines) > 1:
        release_name = lines[1].split()[0]  # Extract the release name from the output
        
        # Step 2: Delete the test-app
        if run_command(f"helm delete {release_name} -n test-app") is None:
            print("Failed to delete Helm release. Exiting.")
            return

        # Step 3: Wait for all pods to be removed
        if not wait_for_pods_removal("test-app"):
            print("Failed during waiting for pod removal. Exiting.")
            return

        # Step 4: List and remove all test-app related PVCs
        pvcs = run_command("kubectl get pvc -n test-app")
        if pvcs is None:
            print("Failed to list PVCs. Exiting.")
            return

        if "No resources found" not in pvcs:
            pvc_names = [line.split()[0] for line in pvcs.splitlines()[1:]]
            if run_command(f"kubectl delete pvc {' '.join(pvc_names)} -n test-app") is None:
                print("Failed to delete PVCs. Exiting.")
                return

    else:
        print("No deployments found in test-app namespace.")

def commit_and_push_changes(branch):
    # Ensure we are on the correct branch
    if run_command(f"git checkout {branch}") is None:
        print(f"Failed to checkout {branch} branch. Exiting.")
        return
    
    # Add changes and commit
    if run_command("git add .") is None:
        print("Failed to add changes. Exiting.")
        return
    if run_command('git commit -m "updated"') is None:
        print("Failed to commit changes. Exiting.")
        return
    
    # Push changes to the remote repository
    if run_command(f"git push origin {branch}") is None:
        print("Failed to push changes. Exiting.")
        return

def update_image_tag_and_version():
    # Get the latest image tag from Jenkins
    image_tag = run_command("git describe")
    if image_tag is None:
        print("Failed to get image tag. Exiting.")
        return

    yaml = YAML()
    yaml.preserve_quotes = True

    # Update the values.yaml file
    with open("charts/test-app/values.yaml", 'r') as file:
        values = yaml.load(file)
    
    values['image']['tag'] = image_tag

    with open("charts/test-app/values.yaml", 'w') as file:
        yaml.dump(values, file)

    # Update the Chart.yaml file
    with open("charts/test-app/Chart.yaml", 'r') as file:
        chart = yaml.load(file)

    current_version = chart['version']
    version_parts = current_version.split('.')
    version_parts[1] = str(int(version_parts[1]) + 1)  # Increment the minor version
    new_version = '.'.join(version_parts)

    chart['version'] = new_version

    with open("charts/test-app/Chart.yaml", 'w') as file:
        yaml.dump(chart, file)

def install_helm_chart():
    # Install the Helm chart
    if run_command("helm install test-app charts/test-app --namespace test-app") is None:
        print("Failed to install Helm chart. Exiting.")
        return

def main():
    print("Select an option:")
    print("1. Cleanup existing version of test-app")
    print("2. Commit and push current changes to Git")
    print("3. Update image tag and version number")
    print("4. Install Helm chart")
    option = int(input("Enter option number: "))

    if option == 1:
        cleanup_test_app()
    elif option == 2:
        commit_and_push_changes(destination_branch)
    elif option == 3:
        update_image_tag_and_version()
    elif option == 4:
        install_helm_chart()
    else:
        print("Invalid option selected")

if __name__ == "__main__":
    main()
