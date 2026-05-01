# kRPC Expressions and Events

## What They Are

kRPC lets you build **expressions** that are evaluated on the game server, not in your Python script. This is useful for:

- Creating **events** that block until a condition is true — without a polling loop in Python
- Composing conditions from live game data with no per-tick RPC round-trips

The two main classes are accessed via `conn.krpc.Expression` and `conn.krpc.Type` (not `krpc.expression.*`):

```python
expr  = conn.krpc.Expression
type_ = conn.krpc.Type
```

---

## Events: Blocking Until a Condition

The most practical use is `conn.space_center.add_event(expr)`, which returns an event object you can wait on:

```python
expr = conn.krpc.Expression
type_ = conn.krpc.Type

# Block until apoapsis altitude > 80,000 m
apo_call = conn.get_call(getattr, vessel.orbit, "apoapsis_altitude")
condition = expr.greater_than(
    expr.call(apo_call),
    expr.constant_double(80_000.0)
)
event = conn.add_event(condition)
with event.condition:
    event.wait()
```

This is more efficient than a `while` loop with `time.sleep` because the check runs inside the game server.

---

## Building Expressions

### Constants

```python
expr.constant_double(9.82)
expr.constant_float(1.0)
expr.constant_int(3)
expr.constant_bool(True)
expr.constant_string("Mun")
```

### Wrapping an RPC Call

Turn any property access or method call into an expression using `conn.get_call`:

```python
call = conn.get_call(getattr, vessel.orbit, "apoapsis_altitude")
live_value = expr.call(call)
```

### Comparisons

All take two sub-expressions and return a boolean expression:

```python
expr.equal(a, b)
expr.not_equal(a, b)
expr.greater_than(a, b)
expr.greater_than_or_equal(a, b)
expr.less_than(a, b)
expr.less_than_or_equal(a, b)
```

### Logic

```python
expr.and_(cond_a, cond_b)
expr.or_(cond_a, cond_b)
expr.not_(cond_a)
expr.exclusive_or(cond_a, cond_b)
```

### Arithmetic

```python
expr.add(a, b)
expr.subtract(a, b)
expr.multiply(a, b)
expr.divide(a, b)
expr.modulo(a, b)
expr.power(base, exponent)
```

### Type Casting

```python
expr.cast(some_expr, type_.double())
```

Available types: `type_.double()`, `type_.float()`, `type_.int()`, `type_.bool()`, `type_.string()`

---

## Collection Expressions

Useful when working with lists of parts, engines, resources, etc.

```python
expr.create_list([expr.constant_double(1.0), expr.constant_double(2.0)])
expr.create_tuple([a, b])
expr.create_set([a, b])
expr.create_dictionary(keys=[k1, k2], values=[v1, v2])

expr.get(collection_expr, index_expr)      # index into list/tuple/dict
expr.count(collection_expr)
expr.sum(collection_expr)
expr.max(collection_expr)
expr.min(collection_expr)
expr.average(collection_expr)
expr.contains(collection_expr, item_expr)

expr.select(collection_expr, func_expr)    # map
expr.where(collection_expr, pred_expr)     # filter
expr.order_by(collection_expr, key_func)
expr.all(collection_expr, pred_expr)
expr.any(collection_expr, pred_expr)
expr.concat(a, b)
expr.to_list(collection_expr)
expr.to_set(collection_expr)
```

---

## Functions and Parameters

You can define reusable server-side lambdas:

```python
param = expr.parameter("x", type_.double())
body = expr.multiply(param, expr.constant_double(2.0))
double_fn = expr.function([param], body)

result = expr.invoke(double_fn, {"x": expr.constant_double(5.0)})
```

---

## When to Use Expressions vs. Streams

| Situation | Use |
|---|---|
| Reading a value every frame in a loop | Stream (`conn.add_stream`) |
| Waiting until a threshold is crossed | Event (`conn.add_event` with Expression) |
| Complex condition combining multiple values | Expression + Event |
| Simple condition, low latency requirements | `wait_until` with a stream |

For most flight control loops, streams are the right tool. Expressions shine for one-shot "wait until X happens" gates — coasting to apoapsis, waiting for SOI change, waiting for a stage to deplete — where a polling loop would waste CPU.

---

## Practical Patterns for a Mun Mission

### Wait for apoapsis altitude to exceed threshold

```python
expr  = conn.krpc.Expression
type_ = conn.krpc.Type

apo_call = conn.get_call(getattr, vessel.orbit, "apoapsis_altitude")
condition = expr.greater_than(
    expr.call(apo_call),
    expr.constant_double(80_000.0)
)
event = conn.add_event(condition)
with event.condition:
    event.wait()
```

### Wait for SOI to change to Mun

Use a polling stream here — SOI changes are rare and a 0.5 s poll is fine:

```python
import time, math

while True:
    t = vessel.orbit.time_to_soi_change
    if not math.isnan(t) and t < 2.0:
        break
    if not math.isnan(t) and t > 60:
        conn.space_center.warp_to(conn.space_center.ut + t - 30)
    time.sleep(0.5)

while vessel.orbit.body.name != "Mun":
    time.sleep(0.1)
```

### Coasting to apoapsis during ascent

Use a stream and a tight poll rather than an expression event — you need to
keep writing telemetry during the coast, so a blocking event is not suitable:

```python
apo_stream = conn.add_stream(getattr, vessel.orbit, "apoapsis_altitude")
target_ap  = 80_000

while apo_stream() < target_ap:
    write_telemetry(tf, vessel, sc, launch_ut, "ASCENT_COAST")
    time.sleep(0.5)
```
