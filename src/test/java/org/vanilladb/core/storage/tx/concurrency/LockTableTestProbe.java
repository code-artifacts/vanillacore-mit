package org.vanilladb.core.storage.tx.concurrency;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
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

	@SuppressWarnings("unchecked")
	private static Map<Object, Object> readMap(LockTable lockTable, String fieldName) {
		try {
			Field field = LockTable.class.getDeclaredField(fieldName);
			field.setAccessible(true);
			return (Map<Object, Object>) field.get(lockTable);
		} catch (ReflectiveOperationException exception) {
			throw new AssertionError("Cannot read LockTable." + fieldName, exception);
		}
	}
}
