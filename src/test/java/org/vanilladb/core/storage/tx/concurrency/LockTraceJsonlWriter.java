package org.vanilladb.core.storage.tx.concurrency;

import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.List;

import org.vanilladb.core.storage.tx.concurrency.trace.LockTraceEvent;

final class LockTraceJsonlWriter {

	private LockTraceJsonlWriter() {
	}

	static void write(Path path, List<LockTraceEvent> events) throws IOException {
		Files.createDirectories(path.getParent());
		try (BufferedWriter writer = Files.newBufferedWriter(path,
				StandardCharsets.UTF_8, StandardOpenOption.CREATE,
				StandardOpenOption.TRUNCATE_EXISTING)) {
			for (LockTraceEvent event : events) {
				writer.write(toJson(event));
				writer.newLine();
			}
		}
	}

	private static String toJson(LockTraceEvent event) {
		StringBuilder json = new StringBuilder(512);
		json.append('{');
		append(json, "schema_version", event.schemaVersion());
		append(json, "run_id", event.runId());
		append(json, "event_id", event.eventId());
		append(json, "thread_id", event.threadId());
		append(json, "thread_seq", event.threadSequence());
		append(json, "tx_id", event.transactionId());
		append(json, "event_type", event.eventType().name());
		append(json, "source_class", event.sourceClass());
		append(json, "source_method", event.sourceMethod());
		append(json, "source_site", event.sourceSite());
		append(json, "resource_kind", event.resourceKind());
		append(json, "resource_id", event.resourceId());
		append(json, "resource_role", event.resourceRole());
		append(json, "parent_resource_id", event.parentResourceId());
		append(json, "lock_purpose", event.lockPurpose());
		append(json, "requested_mode", event.requestedMode());
		append(json, "evidence", event.evidence());
		append(json, "nano_time", event.nanoTime());
		json.setLength(json.length() - 1);
		json.append('}');
		return json.toString();
	}

	private static void append(StringBuilder json, String name, String value) {
		json.append('"').append(name).append("\":");
		if (value == null)
			json.append("null");
		else
			json.append('"').append(escape(value)).append('"');
		json.append(',');
	}

	private static void append(StringBuilder json, String name, long value) {
		json.append('"').append(name).append("\":").append(value).append(',');
	}

	private static String escape(String value) {
		StringBuilder escaped = new StringBuilder(value.length() + 16);
		for (int index = 0; index < value.length(); index++) {
			char character = value.charAt(index);
			switch (character) {
			case '"':
				escaped.append("\\\"");
				break;
			case '\\':
				escaped.append("\\\\");
				break;
			case '\b':
				escaped.append("\\b");
				break;
			case '\f':
				escaped.append("\\f");
				break;
			case '\n':
				escaped.append("\\n");
				break;
			case '\r':
				escaped.append("\\r");
				break;
			case '\t':
				escaped.append("\\t");
				break;
			default:
				if (character < 0x20)
					escaped.append(String.format("\\u%04x", (int) character));
				else
					escaped.append(character);
			}
		}
		return escaped.toString();
	}
}
