# Release Notes

## Version 0.7.0 (2022-09-15)

### Enhancements

- VanillaDB initialization flag is declared volatile. ([#96])
- New work stealing pool for better hand-over latency. ([#96])
- [`Index`](src/main/java/org/vanilladb/core/storage/index/Index.java#L28) blocks and record blocks no longer block each other. ([#96])
- File header pages acquire reentrant latches instead of exclusive locks. ([#96])
- Append no longer performs I/O. ([#96])

[#96]: https://github.com/vanilladb/vanillacore/pull/96

## Version 0.6.0 (2022-02-15)

### Enhancements

- Update [`TransactionProfiler`](src/main/java/org/vanilladb/core/util/TransactionProfiler.java#L27). ([#72][#75][#76])
- Add author. ([#74])
- Optimize buffer & index. ([#78])
- Reduce the call of synchronized block in [`BufferMgr`](src/main/java/org/vanilladb/core/storage/buffer/BufferMgr.java#L52).unpin. ([#79])


[#72]: https://github.com/vanilladb/vanillacore/pull/72
[#74]: https://github.com/vanilladb/vanillacore/pull/74
[#75]: https://github.com/vanilladb/vanillacore/pull/75
[#76]: https://github.com/vanilladb/vanillacore/pull/76
[#78]: https://github.com/vanilladb/vanillacore/pull/78
[#79]: https://github.com/vanilladb/vanillacore/pull/79

## Version 0.5.0 (2021-09-02)

### Enhancements

- Add transaction profilers. ([#69])
- Fix few typos. ([#69])

[#69]: https://github.com/vanilladb/vanillacore/pull/69

## Version 0.4.2 (2021-06-13)

### Enhancements

- Upgrade maven plugins. ([#59])
- Remove deprecated usage of Junit. ([#59])
- Add a test case for concurrent buffer swapping. ([#60])
- Update some comments. ([#60])

[#59]: https://github.com/vanilladb/vanillacore/pull/59
[#60]: https://github.com/vanilladb/vanillacore/pull/60

## Version 0.4.1 (2021-02-24)

### Enhancements

- Improve [`TimerStatistics`](src/main/java/org/vanilladb/core/util/TimerStatistics.java#L25). ([#55])
- Update JUnit to 4.13.2. ([#55])

### Optimizations

- Improve the buffer replacement strategy. ([#55])
	- Add a reference bit to every buffer so that the clock replacement strategy provides more stable performance.
- Remove the cached string from [`BlockId`](src/main/java/org/vanilladb/core/storage/file/BlockId.java#L23). ([#55])
	- Since [`toString`](src/main/java/org/vanilladb/core/storage/file/BlockId.java#L91) of [`BlockId`](src/main/java/org/vanilladb/core/storage/file/BlockId.java#L23) is rarely called, pre-computing the string not only does not help but also wastes resources.

### Code Refactor

- Refactor duplicated code in [`LockTable`](src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L48). ([#50])

### Bug Fixes

- Correct the author name in the [`pom.xml`](pom.xml). ([#48])
- Resolve #49: bad verification while using aggregation fields after an order by clause. ([#54])
- Improve [`IndexUpdatePlannerTest`](src/test/java/org/vanilladb/core/query/planner/index/IndexUpdatePlannerTest.java#L51). ([#55])
	- The name of the indices in the test case might be accidently treated as removable temp files.
- Remove an unstable test case. ([#55])

[#48]: https://github.com/vanilladb/vanillacore/pull/48
[#50]: https://github.com/vanilladb/vanillacore/pull/50
[#54]: https://github.com/vanilladb/vanillacore/pull/54
[#55]: https://github.com/vanilladb/vanillacore/pull/55

## Version 0.4.0 (2020-02-24)

API changes for stored procedures and bug fixes for B-Tree and recovery. ([#44])

### Stored Procedures

- Ensure that [`SpResultSet`](src/main/java/org/vanilladb/core/remote/storedprocedure/SpResultSet.java#L23) saves commit status
- Add missing generic parameters for stored procedures
- Fix the [`toString`](src/main/java/org/vanilladb/core/sql/storedprocedure/SpResultRecord.java#L50) of [`SpResultRecord`](src/main/java/org/vanilladb/core/sql/storedprocedure/SpResultRecord.java#L31)
- Update the visibility of the methods of [`StoredProcedureParamHelper`](#stored-procedures)
- Refactor the design and APIs of stored procedures
- Add a method to manually abort in a stored procedure

### BTree

- Add [`BTreeIndexRecoveryTest`](src/test/java/org/vanilladb/core/storage/tx/recovery/BTreeIndexRecoveryTest.java#L23) for the recovery of B-Tree
- Add [`BTreeIndexConcurrentTest`](src/test/java/org/vanilladb/core/storage/index/btree/BTreeIndexConcurrentTest.java#L30) for the concurrency of B-Tree
- Implement [`toString`](src/main/java/org/vanilladb/core/storage/index/btree/BTreePage.java#L382) for [`BTreePage`](src/main/java/org/vanilladb/core/storage/index/btree/BTreePage.java#L46)
- Fix the bug of searching an entry in [`BTreeDir`](src/main/java/org/vanilladb/core/storage/index/btree/BTreeDir.java#L41)
- Fix the bug of inserting an entry in [`BTreeDir`](src/main/java/org/vanilladb/core/storage/index/btree/BTreeDir.java#L41)
- Add a size check in [`BTreePage`](src/main/java/org/vanilladb/core/storage/index/btree/BTreePage.java#L46)
- Fix a bug that causes overflow while rolling back in BTree

[#44]: https://github.com/vanilladb/vanillacore/pull/44

## Version 0.3.3 (2019-12-16)

All the following changes were merged in [#40].

### Refactoring

- Simplified the result sets of stored procedures

### Enhancements

- Removed unnecessary beforeFirst calls in constructors of Scans
- Made the waiting time in the test cases shorter
- Added more messages for starting up the system
- Reduced memory footprint in Buffers
- Added a new API to [`TransactionMgr`](src/main/java/org/vanilladb/core/storage/tx/TransactionMgr.java#L42)
- Added an error check to [`IndexMgr`](src/main/java/org/vanilladb/core/storage/metadata/index/IndexMgr.java#L45)

### Bug Fixes

- Corrected the implementation of [`ConcurrencyMgr`](src/main/java/org/vanilladb/core/storage/tx/concurrency/ConcurrencyMgr.java#L30)

[#40]: https://github.com/vanilladb/vanillacore/pull/40

## Version 0.3.2 (2018-08-20)

### Bug Fixes

- Fixed the bug of read phantom that created by improper index locking. ([#37])

[#37]: https://github.com/vanilladb/vanillacore/pull/37

## Version 0.3.1 (2018-04-24)

### Bug Fixes

- Fixed the bug causing rolling back a transaction twice ([#32])
- Fixed the error in JavaDoc ([#33])
- Fixed a few bugs after restarting a system from a crash ([#34])

[#32]: https://github.com/vanilladb/vanillacore/pull/32
[#33]: https://github.com/vanilladb/vanillacore/pull/33
[#34]: https://github.com/vanilladb/vanillacore/pull/34

## Version 0.3.0 (2017-10-11)

### Enhancements

- Added DropTable, DropView and DropIndex ([#15], [#21])
- Added Selinger-like planner for query optimization ([#23])
- Added the support of indexing on multiple fields of a table ([#27])

### Code-level Improvements

- Implemented [`Comparable`](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/lang/Comparable.html) for [`RecordId`](src/main/java/org/vanilladb/core/storage/record/RecordId.java#L24) and [`BlockId`](src/main/java/org/vanilladb/core/storage/file/BlockId.java#L23) ([#18])

### Bug Fixes

- Fixed [`NullPointerException`](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/lang/NullPointerException.html) caused by [`GROUP BY`](#bug-fixes) query ([#16])
- Fixed duplicate-postfix problem of B-tree indexes during logging ([#20])
- Fixed the bug that uses too many threads caused by test cases ([#26])

### Others

- Added [`CONTRIBUTING.md`](CONTRIBUTING.md) for the newcomers to know how to contribute ([#22])
- Removed [`develop`](#others) branch and updated the corresponding configuration in [`.travis.yml`](#others) ([#22])

[#15]: https://github.com/vanilladb/vanillacore/pull/15
[#16]: https://github.com/vanilladb/vanillacore/pull/16
[#18]: https://github.com/vanilladb/vanillacore/pull/18
[#20]: https://github.com/vanilladb/vanillacore/pull/20
[#21]: https://github.com/vanilladb/vanillacore/pull/21
[#22]: https://github.com/vanilladb/vanillacore/pull/22
[#23]: https://github.com/vanilladb/vanillacore/pull/23
[#26]: https://github.com/vanilladb/vanillacore/pull/26
[#27]: https://github.com/vanilladb/vanillacore/pull/27

## Version 0.2.2 (2017-06-08)

### Refactoring

- Removed the old interface for initializing [`VanillaDb`](src/main/java/org/vanilladb/core/server/VanillaDb.java#L56) ([#9])
- Maked [`VanillaDb`](src/main/java/org/vanilladb/core/server/VanillaDb.java#L56) accept a [`StoredProcedureFactory`](src/main/java/org/vanilladb/core/sql/storedprocedure/StoredProcedureFactory.java#L18) as a parameter during initialization ([#9], [#10])

### Enhancements

- Added a debug tool, [`org.vanilladb.core.util.Timer`](#enhancements), in order to record the running time in given components for a thread ([#9])

### Bug Fixes

- Maked [`SQLIntepretor`](#bug-fixes) case insensitive to [`SELECT`](#bug-fixes) and [`EXPLAIN`](#bug-fixes) ([#8])

[#8]: https://github.com/vanilladb/vanillacore/pull/8
[#9]: https://github.com/vanilladb/vanillacore/pull/9
[#10]: https://github.com/vanilladb/vanillacore/pull/10

## Version 0.2.1 (2016-09-13)

- Updated Maven configurations
- Deployed the project to Maven Central Repository
- Added Travis CI support for testing
- Fixed some bugs of ARIES-like recovery

## Version 0.2.0

- Replaced the basic recovery algorithm with ARIES-like recovery algorithm
- Added test cases for each component
- Refactored the whole project
  - Removed most unused code
  - Unified the naming of methods

## Version 0.1.0

- Basic function works.
