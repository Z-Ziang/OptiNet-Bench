# Fixed-route spectrum allocation

O1-S outputs `decision` and `slot_start`; a rejection uses `slot_start: null`.
O1-C outputs `decision` and `allocations`. Each accepted allocation contains
`request_id` and `slot_start`, with exactly one allocation per request. A rejection
uses an empty allocation list. Routes are specified in `private/fixed_paths.json`.

The grader combines the predicted slot assignments with the supplied routes and
validates them against the network state and reference objectives. The objective
is to minimize network-wide spectrum fragmentation with the routes fixed.
The underlying structured network objects use the X2/X3 task identifiers; the
catalog identifies the evaluated O1-S/O1-C task. Reference outputs need not be
unique optimal solutions. Only the system and user prompts are sent to models.
