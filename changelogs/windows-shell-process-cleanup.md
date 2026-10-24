# Windows managed Shell cleanup

- Track native Windows managed Shell sessions and their descendants with a Windows Job Object. The Shell is created suspended, assigned to the job, and resumed before executing the command.
- Terminating a session, reaching its timeout, or revoking its execution permissions now terminates descendants even when the original Shell process has already exited. Process and job waits are bounded.
- Release the job handle and captured-output file when process startup fails, and release the job after termination or session removal.
- This fixes the shared local Shell component used by the main Agent; no subagent runtime dependency is introduced. Unix process-group handling is unchanged.
