# Quality Standards

* "Green tests" is the only definition of Done — forced merges on red tests are unacceptable
* All public APIs must have type annotations/signatures
* No data loss: never delete files without backup verification or using reversible operations
* No blind execution: never run generated code without review
* No infinite loops: all autonomous loops must have a maximum iteration count
* Commands like `rm -rf`, `DROP TABLE`, `FORMAT` require explicit user confirmation
* Never delete audit logs or archives without explicit approval and backup
