from daytona import Daytona, DaytonaConfig, CreateSandboxBaseParams

# Initialize the Daytona client
daytona = Daytona(DaytonaConfig(api_key="YOUR_API_KEY"))

# Create the Sandbox instance
sandbox = daytona.create(CreateSandboxBaseParams(language="python"))

# Run code securely inside the Sandbox
response = sandbox.process.code_run('print("Sum of 3 and 4 is " + str(3 + 4))')
if response.exit_code != 0:
    print(f"Error running code: {response.exit_code} {response.result}")
else:
    print(response.result)

# Clean up the Sandbox
daytona.delete(sandbox)