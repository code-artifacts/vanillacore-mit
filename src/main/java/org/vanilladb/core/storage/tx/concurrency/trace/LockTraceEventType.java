package org.vanilladb.core.storage.tx.concurrency.trace;

public enum LockTraceEventType {
	LOCK_CALL,
	WAIT_BEGIN,
	GRANT,
	RELEASE,
	TX_END
}
