package org.vanilladb.core.storage.tx.concurrency;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.Collection;
import java.util.Map;

final class LockTableTestProbe {

	private LockTableTestProbe() {
	}

	static Object anchor(LockTable lockTable, Object resource) {
		try {
			Method method = LockTable.class.getDeclaredMethod("getAnchor", Object.class);
			method.setAccessible(true);
			return method.invoke(lockTable, resource);
		} catch (ReflectiveOperationException exception) {
			throw new AssertionError("Cannot read LockTable anchor", exception);
		}
	}

	static Map<?, ?> lockerMap(LockTable lockTable) {
		return readMap(lockTable, "lockerMap");
	}

	static boolean hasWaitRegistration(LockTable lockTable, long transactionNumber) {
		return readMap(lockTable, "txWaitMap").containsKey(transactionNumber);
	}

	static int lockerCount(LockTable lockTable) {
		return readMap(lockTable, "lockerMap").size();
	}

	static int transactionLockSetCount(LockTable lockTable) {
		return readMap(lockTable, "lockByMap").size();
	}

	static int waitRegistrationCount(LockTable lockTable) {
		return readMap(lockTable, "txWaitMap").size();
	}

	static ResidueSnapshot residueSnapshot(LockTable lockTable) {
		Map<?, ?> lockers = readMap(lockTable, "lockerMap");
		int ownerReferences = 0;
		int requestReferences = 0;
		for (Object locker : lockers.values()) {
			ownerReferences += readCollection(locker, "sLockers").size();
			ownerReferences += readCollection(locker, "ixLockers").size();
			ownerReferences += readCollection(locker, "isLockers").size();
			ownerReferences += readLong(locker, "sixLocker") == -1 ? 0 : 1;
			ownerReferences += readLong(locker, "xLocker") == -1 ? 0 : 1;
			requestReferences += readCollection(locker, "requestSet").size();
		}
		return new ResidueSnapshot(lockers.size(), ownerReferences,
				requestReferences, readMap(lockTable, "lockByMap").size(),
				readMap(lockTable, "txWaitMap").size(),
				readCollection(lockTable, "txnsToBeAborted").size());
	}

	@SuppressWarnings("unchecked")
	private static Map<Object, Object> readMap(LockTable lockTable, String fieldName) {
		return readMap((Object) lockTable, fieldName);
	}

	@SuppressWarnings("unchecked")
	private static Map<Object, Object> readMap(Object owner, String fieldName) {
		try {
			Field field = owner.getClass().getDeclaredField(fieldName);
			field.setAccessible(true);
			return (Map<Object, Object>) field.get(owner);
		} catch (ReflectiveOperationException exception) {
			throw new AssertionError("Cannot read " + fieldName, exception);
		}
	}

	@SuppressWarnings("unchecked")
	private static Collection<Object> readCollection(Object owner,
			String fieldName) {
		try {
			Field field = owner.getClass().getDeclaredField(fieldName);
			field.setAccessible(true);
			return (Collection<Object>) field.get(owner);
		} catch (ReflectiveOperationException exception) {
			throw new AssertionError("Cannot read " + fieldName, exception);
		}
	}

	private static long readLong(Object owner, String fieldName) {
		try {
			Field field = owner.getClass().getDeclaredField(fieldName);
			field.setAccessible(true);
			return field.getLong(owner);
		} catch (ReflectiveOperationException exception) {
			throw new AssertionError("Cannot read " + fieldName, exception);
		}
	}

	static final class ResidueSnapshot {
		final int lockerMapEntries;
		final int ownerReferences;
		final int requestReferences;
		final int transactionLockSetEntries;
		final int waitRegistrationEntries;
		final int abortRegistryEntries;

		private ResidueSnapshot(int lockerMapEntries, int ownerReferences,
				int requestReferences, int transactionLockSetEntries,
				int waitRegistrationEntries, int abortRegistryEntries) {
			this.lockerMapEntries = lockerMapEntries;
			this.ownerReferences = ownerReferences;
			this.requestReferences = requestReferences;
			this.transactionLockSetEntries = transactionLockSetEntries;
			this.waitRegistrationEntries = waitRegistrationEntries;
			this.abortRegistryEntries = abortRegistryEntries;
		}
	}
}
