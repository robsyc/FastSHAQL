<!-- https://w3c.github.io/data-shapes/shacl12-node-expr/ — W3C editors' draft, fetched 2026-08-31 -->

This document defines SHACL 1.2 Node Expressions.

SHACL, the Shapes Constraint Language, is a language for describing the structure of RDF graphs.
The Core of SHACL can be used to define classes and the properties that instances of these classes can have.
More general than classes and instances, SHACL introduces the notion of shapes
that can formally specify constraints on the structure of RDF nodes and edges.

Node Expressions extend SHACL Core primarily to dynamically derive property values
and to compute target nodes of a shape.
To implement these computations, this document defines a library of node expression functions,
including functions from the SPARQL specification, for common use cases.

## SHACL Specifications

This specification is part of the SHACL 1.2 family of specifications. See the [SHACL 1.2 Overview](https://w3c.github.io/data-shapes/shacl12-overview/) for a more detailed introduction to them.

The specifications are as follows:

**Working Drafts:**

[SHACL 1.2 Core](https://www.w3.org/TR/shacl12-core/)
:   defines the Core of SHACL

[SHACL 1.2 Inference Rules](https://www.w3.org/TR/shacl12-inference-rules/)
:   defines SHACL's framework of rule-based inference

[SHACL 1.2 Node Expressions](https://www.w3.org/TR/shacl12-node-expr/)
:   defines expressions used to derive focus nodes and value nodes in SHACL

[SHACL 1.2 Profiling](https://w3c.github.io/data-shapes/shacl12-profiling/)
:   defines the use of SHACL for profiling data, including SHACL data

[SHACL 1.2 SPARQL Extensions](https://www.w3.org/TR/shacl12-sparql/)
:   defines SPARQL-related extensions of SHACL

[SHACL 1.2 UI](https://w3c.github.io/data-shapes/shacl12-ui/)
:   defines SHACL's use for User Interface generation

**Working Group Note Drafts:**

[SHACL 1.2 Overview](https://w3c.github.io/data-shapes/shacl12-overview/)
:   overviews the set of SHACL specifications

[SHACL 1.2 Compact Syntax](https://w3c.github.io/data-shapes/shacl12-cs/)
:   defines an RDF syntax for expressing SHACL concepts

**Note:** Implementers can partially check their level of conformance with the above specifications by successfully passing
the test cases of the [SHACL 1.2 test suite](https://github.com/w3c/data-shapes/tree/gh-pages/shacl12-test-suite).
Note, however, that passing all the tests in the test suite does not imply complete conformance to the specifications.
It only implies that the implementation conforms to the aspects tested by the test suite.

## 1. Introduction

This document specifies SHACL Node Expressions.
This section introduces the key terminology and document conventions.

### 1.1 Terminology

This document uses the terms
RDF graph,
RDF triple,
IRI,
literal,
blank node,
node of an RDF graph,
datatype,
RDF term, and
term equality, and
subject,
predicate, and
object of RDF triples
as defined in RDF 1.2 Concepts and Abstract Syntax rdf12-concepts.

This document uses the terms
focus node,
value,
value node,
constraint,
constraint component,
parameter,
mandatory parameter,
optional parameter,
parameter value,
shape,
node shape,
property shape,
SHACL property path,
data graph,
shapes graph,
target,
validator,
validation result,
node expression,
node expression function,
function name,
output nodes,
focus graph,
evaluation,
evaluation failure,
conforms,
conformance checking,
failure,
validation,
SHACL instance,
SHACL subclass,
SHACL type,
SHACL list,
members,
well-formed,
deep copy,
as defined in the SHACL 1.2 Core specification shacl12-core.

### 1.2 Document Conventions

Some examples in this document use Turtle rdf12-turtle.
The reader is expected to be familiar with SHACL shacl12-core and SPARQL
sparql12-query.

Within this document, the following namespace prefix bindings are used:

| Prefix | Namespace |
| --- | --- |
| `rdf:` | `http://www.w3.org/1999/02/22-rdf-syntax-ns#` |
| `rdfs:` | `http://www.w3.org/2000/01/rdf-schema#` |
| `sh:` | `http://www.w3.org/ns/shacl#` |
| `shnex:` | `http://www.w3.org/ns/shacl-node-expr#` |
| `skos:` | `http://www.w3.org/2004/02/skos/core#` |
| `sparql:` | `http://www.w3.org/ns/sparql#` |
| `xsd:` | `http://www.w3.org/2001/XMLSchema#` |
| `ex:` | `http://example.com/ns#` |

Grey boxes such as this include syntax rules that apply to the shapes graph.

`true`
denotes the RDF term
`"true"^^xsd:boolean`
.
`false`
denotes the RDF term
`"false"^^xsd:boolean`
.

### 1.3 Conformance

This document defines the **SHACL Node Expressions** language that extends shacl12-core.
This specification describes conformance criteria for:

- **SHACL Node Expressions processors** as processors that support the evaluation of SHACL Node Expressions,
  in particular as part of SHACL validation

Also see the discussion of well-formedness in the Conformance section of SHACL Core.

## 2. Getting started with Node Expressions

A SHACL shapes graph can declare node expressions as values of various properties where dynamic computation is useful,
such as `sh:targetNode`, `sh:values`, and `sh:deactivated`.
A node expression is represented by an RDF node and can be evaluated to produce a list of output nodes.
For example, when used at `sh:targetNode`, a node expression produces the list
of target nodes of a shape.
When used at `sh:values`, a node expression produces the derived values for the property specified by `sh:path`.

The following example contains a node expression that states that the target nodes of
the shape `ex:EstonianCompanyShape` are the instances of `ex:Company` where
the `ex:headQuarterCountry` is `ex:Estonia`.

**Example: A node expression used to compute the target nodes of a shape.**

```
ex:EstonianCompanyShape
	a sh:NodeShape ;
	sh:targetNode [
		shnex:nodes [
			shnex:instancesOf ex:Company ;
		] ;
		shnex:filterShape [
			sh:property [
				sh:path ex:headQuarterCountry ;
				sh:hasValue ex:Estonia ;
			]
		]
	] .
					
```

The following diagram illustrates how this node expression is interpreted, from a logical point of view.
During validation, a SHACL processor will determine the target nodes of the shape
by evaluating the filter shape expression.
However, the filter shape expression first evaluates its input expression, which is specified via `sh:nodes`
and is an instancesOf expression.
This will produce all instances of the given class, `ex:Company`.
The `shnex:filterShape` is then applied to all of these instances, to keep only the companies
that conform to the provided shape, by having their headquarters in Estonia.

![Illustration of the data flow between node expressions](images/FilterShapeExampleDiagram.png)

The scenario above can also be expressed using SPARQL select expressions.
For performance reasons, for example, specific implementations of SHACL node expressions might
internally convert node expressions such as the `shnex:filterShape` above to SPARQL.

**Example: A SPARQL select expression used to compute the target nodes of a shape.**

```
ex:EstonianCompanyShape
	a sh:NodeShape ;
	sh:targetNode [
		sh:select """
			SELECT ?company
			WHERE {
				?company rdf:type/rdfs:subClassOf* ex:Company .
				?company ex:headQuarterCountry ex:Estonia .
			}
		"""
	] .
					
```

The next example uses a node expression to compute the values of the property `ex:employeeCount`
as the number of values of the property `ex:employee` at each instance of `ex:Company`.

**Example: A node expression used to compute the values of a derived property.**

```
ex:Company
	a sh:ShapeClass ;
	sh:property ex:Company-employee ;
	sh:property ex:Company-employeeCount .

ex:Company-employee
	a sh:PropertyShape ;
	sh:name "employees" ;
	sh:description "The company's employee(s)." ;
	sh:path ex:employee ;
	sh:class ex:Person .

ex:Company-employeeCount
	a sh:PropertyShape ;
	sh:name "employee count" ;
	sh:description "The number of employees, automatically computed." ;
	sh:path ex:employeeCount ;
	sh:datatype xsd:integer ;
	sh:values [
		shnex:count [
			shnex:pathValues ex:employee ;
		]
	] .
					
```

![Illustration of the data flow between node expressions computing the employee count](images/CountExampleDiagram.png)

One difference between this example and the previous examples about `sh:targetNode`
is that these node expressions are evaluated against a given focus node.
This means that when a data visualization needs to render an instance of `ex:Company`,
the currently displayed company is the focus node, for which the number of employees
will be fetched.

Note that derived properties, such as `ex:employeeCount` from the [example](#employeeCountExample) above,
do not lead to the creation of triples in the data graph or shapes graph.
Tools that use these `sh:values` expressions typically compute the values only on
demand; for example, whenever an instance of `ex:Company` is displayed or queried.

## 3. Node Expression Syntax

This section introduces the general syntax of SHACL node expressions.

The term node expression function refers to the *kind* or *type*
of a node expression.
For example, `sh:FilterShapeExpression` is a node expression function,
while a specific instance of this function in the graph is the node expression itself.

The most basic node expression functions are constant node expressions, which are either
literals, IRIs, or triple terms, and simply evaluate to these constants.
All other node expressions are represented by blank nodes, and come in the following two variations:

- A named parameter function is represented by a blank node that is the subject of one or more
  triples, including the key parameter of the node expression function.
- A list parameter function is comparable to a traditional function in SPARQL, for example,
  and is represented by a blank node that is the subject of a single triple with a SHACL list as its object.

### 3.1 Constant Node Expressions

The node expression functions in this section are called constant node expressions.
Two of them were already introduced in the SHACL Core specification and are repeated here to keep this document self-contained.

#### 3.1.1 IRI Expressions

A node expression that is an IRI is called an IRI expression with the function name
`sh:IRIExpression`.

A node in an RDF graph is a well-formed IRI expression if it is an IRI.

The output nodes of an IRI expression are the list consisting of exactly the node expression itself:
  
  
`evalExpr(expr, focusGraph, focusNode, scope) -> [expr]`

#### 3.1.2 Literal Expressions

A node expression that is a literal is called a literal expression with the function name
`sh:LiteralExpression`.

A node in an RDF graph is a well-formed literal expression if it is a literal.

The output nodes of a literal expression are the list consisting of exactly the node expression itself:
  
  
`evalExpr(expr, focusGraph, focusNode, scope) -> [expr]`

#### 3.1.3 Triple Term Expressions

A node expression that is a triple term is called a triple term expression with the function name
`sh:TripleTermExpression`.

A node in an RDF graph is a well-formed triple term expression if it is a triple term.

The output nodes of a triple term expression are the list consisting of exactly the node expression itself:
  
  
`evalExpr(expr, focusGraph, focusNode, scope) -> [expr]`

### 3.2 Node Expressions based on Blank Nodes

#### 3.2.1 Named Parameter Functions

A named parameter function is a node expression function
that is represented by a blank node that is the subject of at least
one triple where the predicate can be used to uniquely identify the function,
which is known as the key parameter.

The evaluation of a named parameter function can produce any of the following:

- zero output nodes,
  i.e., an empty list
- one or more output nodes,
  i.e., a list of one or more nodes
- an evaluation failure,
  i.e., an (unexpected) error during the evaluation

For example, the named parameter function
[`shnex:FilterShapeExpression`](#FilterShapeExpression)
has `shnex:filterShape` as its key parameter.
In this document, key parameters are marked in **bold face**.

Expressions based on named parameter functions often
take other node expressions as arguments,
evaluate those input node expressions,
and then produce a different list of nodes
as output nodes.

*The remainder of this section is non-normative.*

This document includes many examples of named parameter functions, such as
the [Estonian Company Shape example](#EstonianCompanyShapeExample).

#### 3.2.2 List Parameter Functions

A list parameter function is a node expression function
that is represented by a blank node that is the subject of a single
triple where the object `o` is conforming to one of the following syntax rules, in order:

1. If `o` is the empty SHACL list `rdf:nil` (written as `()` in Turtle)
   then the arguments are the empty list.  
   Example: `[ sparql:now () ]`
2. If `o` is a blank node that is a well-formed SHACL list where all
   members are well-formed node expressions,
   then the arguments are the members of that list.  
   Examples: `[ sparql:plus ( 38 4 ) ]` and `[ sparql:abs ( -42 ) ]`
3. If the function call has one argument,
   and the argument is a well-formed node expression,
   then the argument can be given without the list.
   It is equivalent to a function call with a list of one element.  
   Example: `[ sparql:abs -42 ]`, which is equivalent to
   `[ sparql:abs ( -42 ) ]`.

The predicate of this triple is called the list parameter property.

The evaluation of a list parameter function can produce any of the following:

- one output node, i.e., a list of one node
- zero output nodes, i.e., an empty list
- an evaluation failure, i.e., an (unexpected) error during the evaluation

Furthermore, each argument of a list parameter function must evaluate to an individual, single node,
not to a list of nodes.
If an argument is a node expression, then this node expression must evaluate to
a maximum of one output node.
An evaluation failure must be produced if there is more than one output node.
This is different from named parameter functions, where arguments may produce lists of multiple nodes.

*The remainder of this section is non-normative.*

Note that some named parameter functions — such as `shnex:IntersectionExpression` —
also use a SHACL list as an object of the key parameter, similar to list parameter functions which always have a SHACL list as the object of their list parameter property.
However, these may produce more than one output node, and also accept lists as input nodes.

The following example uses two list parameter functions —
the (hypothetical) `ex:coalesce` and the SPARQL-based `sparql:concat` —
to compute the `ex:displayName`
of a person either as the value of `ex:fullName` or (if that doesn't exist)
as a concatenation of `ex:firstName`, a space, and `ex:lastName`.

**Example: A complex node expression based on list parameter functions.**

```
ex:Person-displayName
	a sh:PropertyShape ;
	sh:name "display name" ;
	sh:path ex:displayName ;
	sh:datatype xsd:string ;
	sh:values [
		ex:coalesce (
			[
				# This is a path values expression that is expected to return zero or one values
				shnex:pathValues ex:fullName ;
			]
			[
				sparql:concat (
					[ shnex:pathValues ex:firstName ]    # Path values expression with at most one value
					" "                                  # A constant literal expression
					[ shnex:pathValues ex:lastName ]     # Path values expression with at most one value
				)
			]
		)
	] .
							
```

### 3.3 Handling of Failures

Node expressions may produce a failure instead of a list of output nodes.
Some node expressions evaluate other, nested node expressions.
For example, [If Expressions](#IfExpression) evaluate nested expressions for
`shnex:if`, `shnex:then` and `shnex:else`.
In general, if any such nested expressions produce a failure then the surrounding
expression also produces the same failure.

*The remainder of this section is non-normative.*

Note that this policy impacts the evaluation order of node expressions.
For example, `shnex:if` expressions are evaluated first and `shnex:then`
will be evaluated only if the `shnex:if` has returned `( true )`.
Even if the `shnex:else` branch would produce a failure, the output would
still only be the output nodes of the `shnex:then` branch.

### 3.4 The Shapes Graph

Some node expression functions — such as [4.2.5 Filter Shape Expressions](#FilterShapeExpression) and [4.5.3 ConformsToShape Expressions](#conformsToShape) —
perform SHACL validation to determine whether a node conforms to a shape.
The shapes graph used for this validation is not explicitly stated for each function.
Instead, it is derived from the context:

1. When a node expression is evaluated as part of another SHACL process
   (e.g., computing value nodes using `sh:values` or target nodes using `sh:targetNode`),
   the shapes graph is reused from the surrounding SHACL process.
2. Otherwise, the shapes graph may be passed into the node expression evaluation process as a parameter.
3. In the absence of such a parameter, the focus graph is used as the shapes graph.

## 4. Node Expressions Library

This section defines all node expression functions that are built into SHACL engines
that implement this specification.

The syntax definitions of node expression functions that are based on blank nodes
typically use a table of properties that these blank nodes can or must have.
Such blank nodes are only well-formed when they are not the subject of any other
triples, and when none of these properties is used more than once.
The tables may also list SHACL constraints with which the property values are required to conform.
In the tables, mandatory properties are rendered in **bold face**.

### 4.1 Basic Node Expressions

#### 4.1.1 Empty Expressions

A blank node that is not the subject of any triple is called an empty expression
with the function name `shnex:EmptyExpression`.

An empty expression has the empty list `[]` as its output nodes.

*The remainder of this section is non-normative.*

This node expression function is written in Turtle as `[]` and must not be confused with
the empty SHACL list `()` which is the IRI `rdf:nil`.

#### 4.1.2 Var Expressions

A blank node that is the subject of the following properties
is called a var expression with the function name `shnex:VarExpression`:

| Property | Constraints | Description |
| --- | --- | --- |
| **`shnex:var`** | `sh:datatype xsd:string`  `sh:minLength 1` | The variable name, e.g. `"focusNode"`. |

Let `var` be the value of `shnex:var` in the var expression.
The output nodes of the var expression are computed as follows, in order:

1. if `var` is `"focusNode"` then `evalExpr(expr, focusGraph, focusNode, scope) -> [focusNode]`
2. if `var` is in the `scope` then `evalExpr(expr, focusGraph, focusNode, scope) -> [ scope[var] ]`
3. otherwise `evalExpr(expr, focusGraph, focusNode, scope) -> []`

*The remainder of this section is non-normative.*

The following example illustrates the use of a var expression pointing at the current focus node
to state that the default value of the `ex:loves` relationship is the current instance of `ex:Person`,
creating a self-reference.

**Example: A var expression stating that any Person loves him or herself by default.**

```
ex:Person
	a sh:ShapeClass ;
	sh:property ex:Person-loves .

ex:Person-loves
	a sh:PropertyShape ;
	sh:path ex:loves ;
	sh:defaultValue [ shnex:var "focusNode" ] .
```

#### 4.1.3 List Expressions

A blank node that is the subject of the following properties
is called a list expression with the function name `shnex:ListExpression`:

| Property | Constraints | Description |
| --- | --- | --- |
| **`rdf:first`** | MUST be a literal or an IRI. | The first member of the list. |
| **`rdf:rest`** | Must be a well-formed SHACL list, where each member is either a literal or an IRI. | The rest of the list, e.g., `rdf:nil`. |

The output nodes of a list expression are the members of the list expression,
in the same order as in the list.

*The remainder of this section is non-normative.*

Note that `rdf:nil` itself is not a list expression because it will be interpreted
as a IRI expression.
As a result, all well-formed list expressions have at least one member.

The following example declares a property for instances of `rdfs:Class`
where the values are derived from the values of the path `rdfs:subClassOf*`
but with the constants from the list `( owl:Thing rdfs:Resource )` removed using
[`shnex:remove`](#RemoveExpression).

**Example: A list expression that is used to enumerate the values of a shnex:remove expression.**

```
ex:ClassShape
	a sh:NodeShape ;
	sh:targetClass rdfs:Class ;
	sh:property ex:ClassShape-superClassesExceptRoots .

ex:ClassShape-superClassesExceptRoots
	a sh:PropertyShape ;
	sh:path ex:superClassesExceptRoots ;
	sh:description "The superclasses of this, except for owl:Thing and rdfs:Resource." ;
	sh:values [
		shnex:nodes [
			# This returns all transitive superclasses of the current focus node
			shnex:pathValues [ sh:zeroOrMorePath rdfs:subClassOf ] ;
		] ;
		# This removes any superclasses that are in the list below
		shnex:remove ( owl:Thing rdfs:Resource ) ;
	] .
							
```

#### 4.1.4 Path Values Expressions

A blank node that is the subject of the following properties
is called a path values expression with the function name `shnex:PathValuesExpression`:

| Property | Constraints | Description |
| --- | --- | --- |
| **`shnex:pathValues`** | Must be a well-formed SHACL property path. | The path to get the values from. |
| `shnex:focusNode` | Optional, must be a well-formed node expression. | A node expression producing the focus node, defaulting to the current focus node from the evaluation context. |

Let `$pathValues` be the value of `shnex:pathValues`,
and `$focusNode` be the value of `shnex:focusNode` in a path values expression.
If `shnex:focusNode` is not given, `$focusNode` is the list consisting of exactly the focus node
from the evaluation context.  
  
Let `N` be the nodes produced by `evalExpr($focusNode, focusGraph, focusNode, scope)`.
If `N` has 0 members, then the output nodes are the empty list.
If `N` has more than 1 member, an evaluation failure is reported.
Otherwise, the output nodes of the path values expression are the list of value nodes of the `path`
for the (only) member of `N`.

**Note:** **Important:** Note the distinction between `sh:path` and `shnex:pathValues`:

- `sh:path` is used in **property shapes** to specify the property path that will be constrained during validation. It defines the property or path to which the shape's constraints apply.
- `shnex:pathValues` is used in **node expressions** to specify the property path that will be traversed to generate a sequence of values. It produces the actual values found by following the path.

For example, `sh:path ex:name` in a property shape constrains the values of the `ex:name` property, while `shnex:pathValues ex:name` in a node expression generates a sequence containing all values of the `ex:name` property.

*The remainder of this section is non-normative.*

Note that by definition, the value nodes of a property shape may be derived properties,
based on `sh:values` or `sh:defaultValue` expressions.
This means that if the provided `shnex:pathValues` path is an IRI, then a path values expression
may cause the evaluation of other node expressions, as a simple kind of rule chaining.

The following example illustrates the use of a path values expression to compute the value
of the property `ex:topConceptCount`.
The expression returns the values of `skos:hasTopConcept` for the current `skos:ConceptScheme`
and these values are processed by the [`shnex:count`](#CountExpression) to return the
number of top concepts.

**Example: A path values expression computing the number of top concepts in a scheme**

```
skos:ConceptScheme
	a sh:ShapeClass ;
	sh:property skos:ConceptScheme-topConceptCount .

skos:ConceptScheme-topConceptCount
	a sh:PropertyShape ;
	sh:path ex:topConceptCount ;
	sh:datatype xsd:integer ;
	sh:description "The number of top concepts in this scheme." ;
	sh:maxCount 1 ;
	sh:name "top concept count" ;
	sh:values [
		shnex:count [
			shnex:pathValues skos:hasTopConcept ;
		] ;
	] .
							
```

The next example illustrates the use of a path values expression together with a specific focus node
(instead of the default focus node provided by the evaluation context).
The shape targets all subjects that have `skos:Concept` as their `rdf:type`
with a dynamically computed `sh:targetNode` expression.
In other words, the target nodes are the direct instances of `skos:Concept` based on asserted
`rdf:type` triples, not including the subclasses of `skos:Concept`.

**Example: A shape that targets the direct instances of skos:Concept, using a path values expression**

```
ex:DirectInstancesOfConceptShape
    a sh:NodeShape ;
    sh:targetNode [
        shnex:pathValues [ sh:inversePath rdf:type ] ;
        shnex:focusNode skos:Concept ;
    ] .
							
```

#### 4.1.5 Exists Expressions

A blank node that is the subject of the following properties
is called an exists expression with the function name `shnex:ExistsExpression`:

| Property | Constraints | Description |
| --- | --- | --- |
| **`shnex:exists`** | A well-formed node expression. | A node expression. If this evaluates to a list with at least one member then the output nodes are `( true )`; otherwise, the output nodes are `( false )`. |

Let `exists` be the value of `shnex:exists` in the exists expression.
Let `N` be the list of nodes produced by `evalExpr(exists, focusGraph, focusNode, scope)`.
The output nodes of the exists expression are `( true )` if and only if
`N` has at least one member; otherwise, the output nodes are `( false )`.

*The remainder of this section is non-normative.*

The [Example for `shnex:if`](#IfExpressionExample) uses `shnex:exists`.

#### 4.1.6 If Expressions

A blank node that is the subject of the following properties
is called an if expression with the function name `shnex:IfExpression`:

| Property | Constraints | Description |
| --- | --- | --- |
| **`shnex:if`** | A well-formed node expression. | A node expression. The `shnex:then` branch is returned when the `shnex:if` expression returns `true` as its only output node, in all other cases `shnex:else`. |
| `shnex:then` | A well-formed node expression. Optional but at least one of `shnex:then` or `shnex:else` is required. | The node expression that is returned when the `shnex:if` evaluated to `[true]`. |
| `shnex:else` | A well-formed node expression. Optional but at least one of `shnex:then` or `shnex:else` is required. | The node expression that is returned when the `shnex:if` did not evaluate to `[true]`. |

Let `if` be the value of `shnex:if`,
`then` be the value of `shnex:then`, and
`else` be the value of `shnex:else` for the if expression.
Let `IFs` be the nodes produced by `evalExpr(if, focusGraph, focusNode, scope)`.
If `IFs` is the list `( true )`, then the output nodes of the if expression
are the nodes produced by `evalExpr(then, focusGraph, focusNode, scope)`, or the empty list if `then` has no value.
Otherwise, the output nodes are the nodes produced by `evalExpr(else, focusGraph, focusNode, scope)`, or the empty list if `else` has no value.
Implementations MUST apply lazy evaluation techniques, so the `shnex:then` or
`shnex:else` branches are only evaluated when necessary.

*The remainder of this section is non-normative.*

The following example illustrates the use of `shnex:if` to compute the
values of a derived property `ex:fillColor` that may be queried to
compute the colors of cities on a map.
In the example, instances of `ex:City` that have a value for `ex:capitalOf`
will be displayed in `"blue"`, while the others will be `"red"`.

**Example: An example "if" expression computing the fill color of a city**

```
ex:City
    a sh:ShapeClass ;
    sh:property ex:City-fillColor .

ex:City-fillColor
    a sh:PropertyShape ;
    sh:path ex:fillColor ;
    sh:datatype xsd:string ;
    sh:name "fill color" ;
    sh:values [
        shnex:if [
            shnex:exists [
                shnex:pathValues ex:capitalOf ;
            ] ;
        ] ;
        shnex:then "blue" ;
        shnex:else "red" ;
    ] .
							
```

### 4.2 List Operator Expressions

#### 4.2.1 Distinct Expressions

A blank node that is the subject of the following properties
is called a distinct expression with the function name `shnex:DistinctExpression`:

| Property | Constraints | Description |
| --- | --- | --- |
| **`shnex:distinct`** | A well-formed node expression. | The node expression that shall be reduced to its distinct members. |

Let `distinct` be the value of `shnex:distinct` in the distinct expression.
Let `input` be the output nodes of `evalExpr(distinct, focusGraph, focusNode, scope)`.
The output nodes of the distinct expression are the list of nodes in `input`
in the same order but with duplicates eliminated (the first occurrences of each node shall be kept, the others removed).
Nodes are compared using term equality, i.e. `"01"^^xsd:integer` is distinct from `"1"^^xsd:integer`.

*The remainder of this section is non-normative.*

The following example declares a derived property `ex:superClassesIncludingRoot`
that is computed as the [concat](#ConcatExpression) of the (transitive) values of `rdfs:subClassOf`
and the [list expression](#ListExpression) `( rdfs:Resource )`.
Since the asserted values of `rdfs:subClassOf` may already include `rdfs:Resource`
(for example, due to an active inference engine on the data graph), `shnex:distinct` will make
sure that the output nodes do not include `rdfs:Resource` twice.

**Example: Using shnex:distinct to return a list of superclasses including rdfs:Resource but not including duplicates**

```
ex:ClassShape
    a sh:NodeShape ;
    sh:targetClass rdfs:Class ;
    sh:property ex:ClassShape-superClassesIncludingRoot .

ex:ClassShape-superClassesIncludingRoot
    a sh:PropertyShape ;
    sh:path ex:superClassesIncludingRoot ;
    sh:description "The superclasses of this, always including rdfs:Resource." ;
    sh:values [
        shnex:distinct [
            shnex:concat (
                [
                    shnex:pathValues [ sh:zeroOrMorePath rdfs:subClassOf ] ;
                ]
                ( rdfs:Resource )
            )
        ] ;
    ] .
							
```

#### 4.2.2 Intersection Expressions

A blank node that is the subject of the following properties
is called an intersection expression with the function name `shnex:IntersectionExpression`:

| Property | Constraints | Description |
| --- | --- | --- |
| **`shnex:intersection`** | A well-formed SHACL list where each member is a well-formed node expression. | The node expressions that shall be intersected. |

Let `members` be the members of the value of `shnex:intersection` in the intersection expression.
The output nodes of the intersection expression are the nodes that form the intersection of the output nodes
produced by each node expression `NE` in `members`, using `evalExpr(NE, focusGraph, focusNode, scope)`.
Nodes must be equal using term equality, e.g., `"01"^^xsd:integer` is distinct from `"1"^^xsd:integer`.
The intersection does not include duplicates and the order is undefined.

*The remainder of this section is non-normative.*

The following example uses `shnex:intersection` as a `sh:targetNode` node expression.
This shape will target all nodes that are SHACL instances of `ex:Australian` and
`ex:German` at the same time.

**Example: Using shnex:intersection to compute the target nodes of a shape**

```
ex:DualCitizenShape
    a sh:NodeShape ;
    sh:targetNode [
        shnex:intersection (
            [ shnex:instancesOf ex:Australian ]
            [ shnex:instancesOf ex:German ]
        )
    ] .
							
```

**Evaluation trace:**

The evaluation proceeds as follows:

1. `shnex:instancesOf ex:Australian`
   produces: `[ex:Person1, ex:Person2, ex:Person3, ex:Person4]`
2. `shnex:instancesOf ex:German`
   produces: `[ex:Person2, ex:Person4, ex:Person5]`
3. Compute the intersection (nodes appearing in both lists):
   `[ex:Person2, ex:Person4]`

More abstractly, the intersection of `[1, 2, 3, 4]` and `[2, 4, 5]` results in `[2, 4]`,
containing only the elements that appear in both lists.

#### 4.2.3 Concat Expressions

A blank node that is the subject of the following properties
is called a concat expression, with the function name `shnex:ConcatExpression`:

| Property | Constraints | Description |
| --- | --- | --- |
| **`shnex:concat`** | A well-formed SHACL list where each member is a well-formed node expression. | The node expressions that shall be concatenated. |

Let `members` be the members of the value of `shnex:concat` in the concat expression.
The output nodes of the concat expression are the concatenation of all output nodes
for each node expression `NE` in `members`, using `evalExpr(NE, focusGraph, focusNode, scope)`.
The order is preserved, evaluating the `members` from left to right and keeping the order of each list of output nodes.

*The remainder of this section is non-normative.*

Note that a concat expression may produce duplicate output nodes if the individual output nodes overlap.
Use [shnex:distinct](#DistinctExpression) to eliminate duplicates.

The following example declares a derived property `ex:allRelatives`
that concatenates the values of `ex:parent` and `ex:sibling`.
The `shnex:concat` expression takes a list of node expressions and returns
all nodes from each expression in sequence from left to right.

**Example: Using shnex:concat to combine results from multiple node expressions**

```
ex:PersonShape
	a sh:NodeShape ;
	sh:targetClass ex:Person ;
	sh:property ex:PersonShape-allRelatives .

ex:PersonShape-allRelatives
	a sh:PropertyShape ;
	sh:path ex:allRelatives ;
	sh:class ex:Person ;
	sh:name "all relatives" ;
	sh:values [
		shnex:concat (
			[ shnex:pathValues ex:parent ]
			[ shnex:pathValues ex:sibling ]
		)
	] .
							
```

**Evaluation trace:**

The evaluation proceeds as follows:

1. `shnex:pathValues ex:parent` with focus node `ex:Person1`
   produces: `[ex:Parent1, ex:Parent2]`
2. `shnex:pathValues ex:sibling` with focus node `ex:Person1`
   produces: `[ex:Sibling1, ex:Sibling2, ex:Sibling3]`
3. Concatenate the results in order:
   `[ex:Parent1, ex:Parent2, ex:Sibling1, ex:Sibling2, ex:Sibling3]`

More abstractly, concatenating `[1, 2]` and `[3, 4, 5]` results in `[1, 2, 3, 4, 5]`
with all elements preserved in order from left to right.

#### 4.2.4 Remove Expressions

A blank node that is the subject of the following properties
is called a remove expression, with the function name `shnex:RemoveExpression`:

| Property | Constraints | Description |
| --- | --- | --- |
| **`shnex:remove`** | A well-formed node expression. | The nodes that shall be removed from the `shnex:nodes`. |
| **`shnex:nodes`** | A well-formed node expression. | The input nodes. |

Let `remove` be the value of `shnex:remove`
and `nodes` be the value of `shnex:nodes` in the remove expression.
Let `M` be the output nodes of `evalExpr(remove, focusGraph, focusNode, scope)`.
Let `N` be the output nodes of `evalExpr(nodes, focusGraph, focusNode, scope)`.
The output nodes of the remove expression are the nodes in `N`
except those that are also in `M`, preserving the order of `N`.
Nodes must be equal using term equality, i.e., `"01"^^xsd:integer` is distinct from `"1"^^xsd:integer`.

*The remainder of this section is non-normative.*

The following example declares a derived property, `ex:availableAuthors`,
that returns all persons who are authors, except those who are currently on leave.
The `shnex:remove` expression takes the nodes from `shnex:nodes` (all authors)
and removes the nodes returned by the `shnex:remove` expression (authors on leave).

**Example: Using shnex:remove to exclude unavailable authors from a list**

```
ex:PublisherShape
	a sh:NodeShape ;
	sh:targetClass ex:Publisher ;
	sh:property ex:PublisherShape-availableAuthors .

ex:PublisherShape-availableAuthors
	a sh:PropertyShape ;
	sh:path ex:availableAuthors ;
	sh:class ex:Person ;
	sh:description "Authors who are currently available (not on leave)." ;
	sh:values [
		shnex:nodes  [ shnex:pathValues ex:author ] ; 		  
		shnex:remove [ shnex:pathValues ex:authorOnLeave ] ;  
	] .
							
```

**Evaluation trace:**

The evaluation proceeds as follows:

1. `shnex:nodes [shnex:pathValues ex:author]` with focus node `ex:PublisherA`
   produces: `[ex:Author1, ex:Author1, ex:Author1, ex:Author2, ex:Author2]`
2. `shnex:remove [shnex:pathValues ex:authorOnLeave]` with focus node `ex:PublisherA`
   produces: `[ex:Author1, ex:Author1]`
3. Remove all occurrences of `ex:Author1` from the nodes list, preserving order:
   `[ex:Author2, ex:Author2]`

More abstractly, removing `[1, 1]` from `[1, 1, 1, 2, 2]` results in `[2, 2]`
because all instances of `1` are removed (not just the first occurrence).

#### 4.2.5 Filter Shape Expressions

A blank node that is the subject of the following properties
is called a filter shape expression with the function name `shnex:FilterShapeExpression`:

| Property | Constraints | Description |
| --- | --- | --- |
| **`shnex:filterShape`** | A well-formed shape. | The shape that all input nodes need to conform to. |
| **`shnex:nodes`** | A well-formed node expression. | A node expression producing the nodes that are validated. |

Let `filterShape` be the value of `shnex:filterShape`,
and `nodes` be the value of `shnex:nodes` in a filter shape expression.
The output nodes of the filter shape expression are the output nodes of
`evalExpr(nodes, focusGraph, focusNode, scope)` except those that do not conform to
the shape `filterShape`, preserving the order in the list.

*The remainder of this section is non-normative.*

The following example illustrates the use of `shnex:filterShape` to return a subset
of values of the `ex:child` property where the `ex:gender` property
has the value `"male"`.

**Example: Using shnex:filterShape to compute the children that are male**

```
ex:Person
    a sh:ShapeClass ;
    sh:property ex:Person-maleChildren .

ex:Person-maleChildren
    a sh:PropertyShape ;
    sh:path ex:maleChildren ;
    sh:class ex:Person ;
    sh:values [
        shnex:nodes [
            shnex:pathValues ex:child ;
        ] ;
        shnex:filterShape [
            sh:property [
                sh:path ex:gender ;
                sh:hasValue "male" ;
            ]
        ] ;
    ] .
							
```

#### 4.2.6 Limit Expressions

A blank node that is the subject of the following properties
is called a limit expression with the function name `shnex:LimitExpression`:

| Property | Constraints | Description |
| --- | --- | --- |
| **`shnex:limit`** | `sh:datatype xsd:integer`  `sh:minInclusive 0` | The maximum number of nodes that shall be returned. |
| **`shnex:nodes`** | A well-formed node expression. | The input nodes. |

Let `limit` be the value of `shnex:limit`
and `nodes` be the value of `shnex:nodes` in the limit expression.
Let `N` be the output nodes of `evalExpr(nodes, focusGraph, focusNode, scope)`.
The output nodes of the limit expression are the first `limit` nodes in `N`
from left to right, in the same order.

*The remainder of this section is non-normative.*

The following example illustrates the use of `shnex:limit` to compute the
values of a derived property `ex:oldestChildren` to be a sub-list of
values of `ex:child` at the current focus node (which is an instance of
the class `ex:Person`).
The values are computed by first fetching the values of `ex:child`, then
ordering them by their `ex:dateOfBirth`, and finally getting only
`2` of these children at most.

**Example: Using shnex:limit and shnex:orderBy to compute the oldest two children**

```
ex:PersonShape
    a sh:NodeShape ;
    sh:targetClass ex:Person ;
    sh:property ex:PersonShape-oldestTwoChildren .

ex:PersonShape-oldestTwoChildren
    a sh:PropertyShape ;
    sh:path ex:oldestTwoChildren ;
    sh:class ex:Person ;
    sh:values [
        shnex:nodes [
            shnex:nodes [
                shnex:pathValues ex:child ;
            ] ;
            shnex:orderBy [
                shnex:pathValues ex:dateOfBirth ;
            ] ;
        ] ;
        shnex:limit 2 ;
    ] .
							
```

#### 4.2.7 Offset Expressions

A blank node that is the subject of the following properties
is called an offset expression with the function name `shnex:OffsetExpression`:

| Property | Constraints | Description |
| --- | --- | --- |
| **`shnex:offset`** | `sh:datatype xsd:integer`  `sh:minInclusive 0` | The number of nodes that shall be skipped from the `shnex:nodes`. |
| **`shnex:nodes`** | A well-formed node expression. | The input nodes. |

Let `offset` be the value of `shnex:offset`
and `nodes` be the value of `shnex:nodes` in the offset expression.
Let `N` be the output nodes of `evalExpr(nodes, focusGraph, focusNode, scope)`.
The output nodes of the offset expression are the nodes in `N`
except for the first `offset` nodes from left to right, in the same order.

*The remainder of this section is non-normative.*

The following example illustrates the use of `shnex:offset` to compute the
values of a derived property `ex:remainingChildren` to be a sub-list of
values of `ex:child` at the current focus node (which is an instance of
the class `ex:Person`).
The values are computed by first fetching the values of `ex:child`, then
ordering them by their `ex:dateOfBirth`, and finally skipping the first
of these children.

**Example: Using shnex:offset to compute all but the oldest child**

```
ex:PersonShape
    a sh:NodeShape ;
    sh:targetClass ex:Person ;
    sh:property ex:PersonShape-remainingChildren .

ex:PersonShape-remainingChildren
    a sh:PropertyShape ;
    sh:path ex:remainingChildren ;
    sh:class ex:Person ;
    sh:values [
        shnex:nodes [
            shnex:nodes [
                shnex:pathValues ex:child ;
            ] ;
            shnex:orderBy [
                shnex:pathValues ex:dateOfBirth ;
            ] ;
        ] ;
        shnex:offset 1 ;
    ] .
							
```

#### 4.2.8 OrderBy Expressions

A blank node that is the subject of the following properties
is called an order by expression with the function name `shnex:OrderByExpression`:

| Property | Constraints | Description |
| --- | --- | --- |
| **`shnex:nodes`** | A well-formed node expression. | The input nodes. |
| **`shnex:orderBy`** | A well-formed node expression. | The node expression that is applied to each input node. |
| `shnex:desc` | `sh:datatype xsd:boolean` | `true` to produce descending order, defaults to `false`. |

Let `orderBy` be the value of `shnex:orderBy`,
`nodes` be the value of `shnex:nodes` and
`desc` be the value of `shnex:desc` in the order by expression.
Let `N` be the output nodes of `evalExpr(nodes, focusGraph, focusNode, scope)`.
Let `c(n)` be the first output node of `evalExpr(orderBy, focusGraph, n, scope)`
for each `n` in `N`.
The output nodes of the order by expression are the nodes in `N`
sorted by `c(n)` using the same logic as SPARQL ORDER BY.
Nodes where `c(n)` is unbound are considered smaller than those that have any value.
If `desc` is `true` then the output nodes are returned in the reverse order.

*The remainder of this section is non-normative.*

The [Example of `shnex:limit`](#LimitExpressionExample) also illustrates `shnex:orderBy`.

### 4.3 Advanced Sequence Operations

#### 4.3.1 FlatMap Expressions

A blank node that is the subject of the following properties
is called a flat map expression,
with the function name `shnex:FlatMapExpression`:

| Property | Constraints | Description |
| --- | --- | --- |
| **`shnex:flatMap`** | A well-formed node expression. | The node expression that is applied to each input node. |
| `shnex:nodes` | A well-formed node expression. | The input nodes. If omitted, defaults to the focus node. |

Let `flatMap` be the value of `shnex:flatMap`
and `nodes` be the value of `shnex:nodes` in a flat map expression.
If `shnex:nodes` is not specified, let `nodes` be the focus node.

Let `N` be the output nodes of
`evalExpr(nodes, focusGraph, focusNode, scope)`.

For each node `n` in `N`, let `Mn` be the output nodes of
`evalExpr(flatMap, focusGraph, n, scope)`.

The output nodes of the flat map expression are produced by concatenating all sequences
`Mn` in the order of the corresponding nodes `n` in `N`.

*The remainder of this section is non-normative.*

The `shnex:flatMap` operation applies an expression to each input node and flattens the results
into a single sequence. This is particularly useful when combining results from multiple path traversals
or when working with nested structures.

A key aspect of `shnex:flatMap` is that the focus node changes for each iteration.
For each node produced by the `shnex:nodes` expression, that node becomes the focus node
when evaluating the `shnex:flatMap` expression. This allows relative path expressions to work correctly
at each level of nesting. The output sequences are then concatenated in order, preserving both the order
of input nodes and the order of results within each output sequence.

Unlike operations that remove duplicates, `shnex:flatMap` preserves all results, including duplicates.
If duplicate elimination is desired, use `shnex:distinct` to post-process the results.

The following example illustrates the use of `shnex:flatMap` to derive a property
`ex:allSkills` that collects all skills from all employees of a company.
For each employee of the company, the flatMap operation applies a path expression to retrieve their skills,
and flattens the resulting skill sequences into a single comprehensive list.

**Example: Using shnex:flatMap to collect skills from all employees**

```
ex:CompanyShape
    a sh:NodeShape ;
    sh:targetClass ex:Company ;
    sh:property ex:CompanyShape-allSkills .

ex:CompanyShape-allSkills
    a sh:PropertyShape ;
    sh:path ex:allSkills ;
    sh:name "all skills" ;
    sh:values [
        shnex:nodes [
            shnex:pathValues ex:employee ;
        ] ;
        shnex:flatMap [
            shnex:pathValues ex:skill ;
        ] ;
    ] .
							
```

```
ex:CompanyA
    ex:employee ex:Employee1 ;
    ex:employee ex:Employee2 ;
    ex:employee ex:Employee3 .

ex:Employee1
    ex:skill "Java"@en ;
    ex:skill "Python"@en ;
    ex:skill "SQL"@en .

ex:Employee2
    ex:skill "Python"@en ;
    ex:skill "JavaScript"@en .

ex:Employee3
    ex:skill "Java"@en ;
    ex:skill "DevOps"@en .
							
```

**Evaluation trace:**

1. `shnex:nodes [shnex:pathValues ex:employee]` with focus node `ex:CompanyA`
   produces: `[ex:Employee1, ex:Employee2, ex:Employee3]`
2. For each employee `n`, evaluate `shnex:flatMap [shnex:pathValues ex:skill]`
   with focus node `n`:
   - `ex:Employee1` → `["Java", "Python", "SQL"]`
   - `ex:Employee2` → `["Python", "JavaScript"]`
   - `ex:Employee3` → `["Java", "DevOps"]`
3. Combine all results in order:
   `["Java", "Python", "SQL", "Python", "JavaScript", "Java", "DevOps"]`
4. Optional: Refine the resulting sequence using for example:
   - `shnex:distinct` to remove duplicates from the flattened result.
   - `shnex:filterShape` to apply an additional shape constraint to the
     flattened nodes.
   - `shnex:limit` to restrict the flattened result to the first N nodes.

#### 4.3.2 FindFirst Expressions

A blank node that is the subject of the following properties
is called a find first expression,
with the function name `shnex:FindFirstExpression`:

| Property | Constraints | Description |
| --- | --- | --- |
| **`shnex:findFirst`** | A well-formed shape. | The shape that the matching node must conform to. |
| `shnex:nodes` | A well-formed node expression. | The input nodes. If omitted, defaults to the focus node. |

Let `shape` be the value of `shnex:findFirst`
and `nodes` be the value of `shnex:nodes` in a find first expression.
If `shnex:nodes` is not specified, let `nodes` be the focus node.
Let `N` be the output nodes of `evalExpr(nodes, focusGraph, focusNode, scope)`.
The output nodes of the find first expression contain exactly the first node `n`
in `N` that conforms to the shape `shape`,
or an empty sequence if no such node exists.

*The remainder of this section is non-normative.*

The `shnex:findFirst` operation finds the first node in a sequence that conforms to a given shape.

The following example illustrates the use of `shnex:findFirst` to derive a property
`ex:seniorEmployee` that finds the first employee with more than five years of experience.
The `shnex:findFirst` operation tests each employee against a shape that validates their years of service.

**Example: Using shnex:findFirst to find the first senior employee**

```
ex:CompanyShape
    a sh:NodeShape ;
    sh:targetClass ex:Company ;
    sh:property ex:CompanyShape-seniorEmployee .

ex:CompanyShape-seniorEmployee
    a sh:PropertyShape ;
    sh:path ex:seniorEmployee ;
    sh:class ex:Employee ;
    sh:maxCount 1 ;
    sh:name "senior employee" ;
    sh:values [
		shnex:nodes [
			shnex:pathValues ex:employee ;
		] ;
		shnex:findFirst ex:SeniorEmployeeShape ;
    ] .

ex:SeniorEmployeeShape
    a sh:NodeShape ;
    sh:property [
        sh:path ex:yearsOfService ;
        sh:datatype xsd:integer ;
        sh:minInclusive 5 ;
    ] .
							
```

#### 4.3.3 MatchAll Expressions

A blank node that is the subject of the following properties
is called a match all expression,
with the function name `shnex:MatchAllExpression`:

| Property | Constraints | Description |
| --- | --- | --- |
| **`shnex:matchAll`** | A well-formed shape. | The shape that all input nodes must conform to. |
| `shnex:nodes` | A well-formed node expression. | The input nodes. If omitted, defaults to the focus node. |

Let `shape` be the value of `shnex:matchAll`
and `nodes` be the value of `shnex:nodes` in the match all expression.
If `shnex:nodes` is not specified, let `nodes` be the focus node.
Let `N` be the output nodes of `evalExpr(nodes, focusGraph, focusNode, scope)`.
The output nodes of the match all expression are `( true )` if
every node `n` in `N` conforms to the shape `shape`;
otherwise the output nodes are `( false )`.

*The remainder of this section is non-normative.*

The `shnex:matchAll` operation returns `true` if all nodes in a sequence conform to a given shape,
`false` otherwise.

The following example illustrates the use of `shnex:matchAll` to derive a property
`ex:allEmployeesActive` that checks whether all employees of a company are currently active.
The match all operation tests each employee against a shape that validates their active status.

**Example: Using shnex:matchAll to verify all employees are active**

```
ex:CompanyShape
    a sh:NodeShape ;
    sh:targetClass ex:Company ;
    sh:property ex:CompanyShape-allEmployeesActive .

ex:CompanyShape-allEmployeesActive
    a sh:PropertyShape ;
    sh:path ex:allEmployeesActive ;
    sh:datatype xsd:boolean ;
    sh:maxCount 1 ;
    sh:name "all employees active" ;
    sh:values  [
		shnex:nodes [
			shnex:pathValues ex:employee ;
		] ;
		shnex:matchAll ex:ActiveEmployeeShape ;
    ] .

ex:ActiveEmployeeShape
    a sh:NodeShape ;
    sh:property [
        sh:path ex:isActive ;
        sh:hasValue true ;
    ] .
							
```

### 4.4 Aggregation Expressions

#### 4.4.1 Count Expressions

A blank node that is the subject of the following properties
is called a count expression with the function name `shnex:CountExpression`:

| Property | Constraints | Description |
| --- | --- | --- |
| **`shnex:count`** | A well-formed node expression. | The input nodes that shall be counted. |

Let `count` be the value of `shnex:count` in the count expression.
Let `N` be the output nodes of `evalExpr(count, focusGraph, focusNode, scope)`.
The output nodes of the count expression is the list consisting of exactly one
`xsd:integer` literal that is computed as the length of `N`.

*The remainder of this section is non-normative.*

The following example illustrates the use of `shnex:count` to derive a property
`ex:topConceptCount` as the number of values of the `skos:hasTopConcept`
property in a `skos:ConceptScheme`.

**Example: Using shnex:count to compute the number of values of another property**

```
skos:ConceptScheme
    a rdfs:Class, sh:NodeShape ;
    sh:property skos:ConceptScheme-topConceptCount .

skos:ConceptScheme-topConceptCount
    a sh:PropertyShape ;
    sh:path ex:topConceptCount ;
    sh:datatype xsd:integer ;
    sh:description "The number of top concepts in this scheme." ;
    sh:maxCount 1 ;
    sh:name "top concept count" ;
    sh:values [
        shnex:count [
            shnex:pathValues skos:hasTopConcept ;
        ] ;
    ] .
							
```

#### 4.4.2 Min Expressions

A blank node that is the subject of the following properties
is called a min expression with the function name `shnex:MinExpression`:

| Property | Constraints | Description |
| --- | --- | --- |
| **`shnex:min`** | A well-formed node expression. | The input nodes from which the minimum value shall be returned. |

Let `min` be the value of `shnex:min` in the min expression.
Let `N` be the output nodes of `evalExpr(min, focusGraph, focusNode, scope)`.
The output nodes of the min expression is the list consisting of at most one node
that is computed as the minimum value from `N`,
see SPARQL MIN.

*The remainder of this section is non-normative.*

The following example illustrates the use of `shnex:min` to derive a property
`ex:minStartDate` as the smallest value of the values that can be reached using the
property path `ex:employee/ex:startDate`.
In other words, it walks through all employees of the given company and returns the earliest
date on which an employee started.

**Example: Using shnex:min to compute the smallest value in a property path**

```
ex:CompanyShape
    a sh:NodeShape ;
    sh:targetClass ex:Company ;
    sh:property ex:CompanyShape-minStartDate .

ex:CompanyShape-minStartDate
    a sh:PropertyShape ;
    sh:path ex:minStartDate ;
    sh:datatype xsd:date ;
    sh:maxCount 1 ;
    sh:name "min start date" ;
    sh:values [
        shnex:min [
            shnex:pathValues ( ex:employee ex:startDate ) ;
        ] ;
    ] .
							
```

#### 4.4.3 Max Expressions

A blank node that is the subject of the following properties
is called a max expression with the function name `shnex:MaxExpression`:

| Property | Constraints | Description |
| --- | --- | --- |
| **`shnex:max`** | A well-formed node expression. | The input nodes from which the maximum value shall be returned. |

Let `max` be the value of `shnex:max` in the max expression.
Let `N` be the output nodes of `evalExpr(max, focusGraph, focusNode, scope)`.
The output nodes of the max expression is the list consisting of at most one node
that is computed as the maximum value from `N`,
see SPARQL MAX.

*The remainder of this section is non-normative.*

The [Example for `shnex:min`](#MinExpressionExample) can be easily adapted
for `shnex:max`.

#### 4.4.4 Sum Expressions

A blank node that is the subject of the following properties
is called a sum expression with the function name `shnex:SumExpression`:

| Property | Constraints | Description |
| --- | --- | --- |
| **`shnex:sum`** | A well-formed node expression. | The input nodes from which the sum shall be returned. |

Let `sum` be the value of `shnex:sum` in the sum expression.
Let `N` be the output nodes of `evalExpr(sum, focusGraph, focusNode, scope)`.
The output nodes of the sum expression is the list consisting of exactly one node
that is computed as the sum of all nodes from `N`,
see SPARQL SUM.

*The remainder of this section is non-normative.*

Note that `shnex:sum` needs to be used with care and may be misunderstood,
when used with property paths.
The problem is that when a path values expression is used as input to a sum expression,
the path values expression will have eliminated duplicates before they can be processed by the `shnex:sum`.
As a result, only the distinct values will be added up.
To work around this, one option is to use SPARQL-based node expressions.
Another alternative is illustrated in the following example.

**Example: Using shnex:sum to compute the sum of the revenues of all departments**

```
ex:CompanyShape
    a sh:NodeShape ;
    sh:targetClass ex:Company ;
    sh:property ex:CompanyShape-totalRevenue .

ex:CompanyShape-totalRevenue
    a sh:PropertyShape ;
    sh:path ex:totalRevenue ;
    sh:datatype xsd:decimal ;
    sh:maxCount 1 ;
    sh:name "total revenue" ;
    sh:values [
        shnex:sum [
            shnex:nodes [
                shnex:pathValues ex:department ;
            ] ;
            shnex:flatMap [
                shnex:pathValues ex:revenue ;
            ] ;
        ] ;
    ] .
							
```

For the following data graph, the sum will be `42.0`.

```
ex:MyCompany
    a ex:Company ;
    ex:department [
	    ex:revenue 2.1 ;
    ] ;
    ex:department [
        ex:revenue 37.8 ;
    ] ;
    ex:department [
        ex:revenue 2.1 ;
    ] .
							
```

In this example, the system will first fetch all values of `ex:department` for the current company.
Then, for each of these departments, it will get the values for `ex:revenue` via a flat map expression
and finally return the sum of those numbers.

### 4.5 Miscellaneous Node Expressions

This section enumerates node expression functions that did not fit into other categories.

#### 4.5.1 InstancesOf Expressions

A blank node that is the subject of the following properties
is called an instancesOf expression with the function name `shnex:InstancesOfExpression`:

| Property | Constraints | Description |
| --- | --- | --- |
| **`shnex:instancesOf`** | A well-formed node expression. | A node expression returning the class(es) that the output nodes must be instances of. |

Let `typesExpr` be the value of `shnex:instancesOf` in an instancesOf expression.
Let `types` be the output nodes of `evalExpr(typesExpr, focusGraph, focusNode, scope)`.
An evaluation failure is reported when any of the members of `types` is not an IRI.
The output nodes of the instancesOf expression are the distinct nodes that are SHACL instances
in the focus graph of each member of `types`.

*The remainder of this section is non-normative.*

Note that the definition of `SHACL instance` includes instances of subclasses of the given class.
So if the focus graph contains `ex:SubClass rdfs:subClassOf ex:SuperClass` and `ex:SubInstance a ex:SubClass`
then `ex:SubInstance` will also be returned as instance of `ex:SuperClass`.

The interpretation of `shnex:instancesOf` is similar to `sh:targetClass` and `sh:class`.

Users of this node expression function should be aware that the list of output nodes may be very large.

The [Example for `shnex:intersection`](#IntersectionExpressionExample) uses `shnex:instancesOf`.

#### 4.5.2 Nodes Matching Expressions

A blank node that is the subject of the following properties
is called a nodes matching expression with the function name `shnex:NodesMatchingExpression`:

| Property | Constraints | Description |
| --- | --- | --- |
| **`shnex:nodesMatching`** | Must be a well-formed shape. | The shape that the output nodes must conform to. |

Let `shape` be the value of `shnex:nodesMatching` in a nodes matching expression.
The output nodes of the nodes matching expression are the nodes in the focus graph
that conform to `shape`.

*The remainder of this section is non-normative.*

Users of this node expression function should be aware that the list of output nodes may be very large
and that some implementations may not be able to efficiently process it.

The following example illustrates the use of `shnex:nodesMatching` to compute all instances of
`ex:Company` that have at least 100 employees.

```
ex:LargeCompanyShape
    a sh:NodeShape ;
    sh:targetNode [
        shnex:nodesMatching [
            sh:class ex:Company ;
            sh:property [
                sh:path ex:employee ;
                sh:minCount 100 ;
            ]
        ]
    ] .
							
```

The interpretation of `shnex:nodesMatching` is similar to `sh:targetWhere`.
The main differences are that `sh:targetWhere` is part of SHACL Core and that
`shnex:nodesMatching` can be used in arbitrary node expressions.

#### 4.5.3 ConformsToShape Expressions

A blank node that has a SHACL list with two members
as its value for `shnex:conformsToShape`
is called a conformsToShape expression with the function name `shnex:conformsToShape`.
The two members are as follows:

| Argument | Constraints | Description |
| --- | --- | --- |
| **`node`** |  | A node expression producing the node that is validated. |
| **`shape`** | `sh:nodeKind sh:IRI`  Must produce the IRI of a well-formed shape. | A node expression producing the shape that the node is validated against. |

Note that `shnex:conformsToShape` is a list parameter function which means that
it returns at most one output node and
the members of the arguments list are node expressions that must produce at most one output node each.
Consequently, if the `shape` argument is a blank node, then it will be interpreted as
a node expression, not as a shape.

Let `nodeExpr` be the first argument of a conformsToShape expression.
Let `node` be the (single) result of `evalExpr(nodeExpr, focusGraph, focusNode, scope)`.
Let `shapeExpr` be the second argument of a conformsToShape expression.
Let `shape` be the (single) result of `evalExpr(shapeExpr, focusGraph, focusNode, scope)`.
The output nodes of the conformsToShape expression are the empty list
if either `node` or `shape` have no value.
Otherwise, the output nodes are
`( true )` if and only if `node` conforms to `shape` (using the [derived shapes graph](#the-shapes-graph) for the shape definition and the focus graph as the data graph),
and `( false )` otherwise.
An evaluation failure is produced if the validation of the node
against the shape causes a failure.

*The remainder of this section is non-normative.*

**Example: Using shnex:conformsToShape to derive a boolean property**

```
ex:HasDirectorShape
    a sh:NodeShape ;
    sh:property [
		sh:path ex:director ;
		sh:minCount 1 ;
	] .

ex:CompanyShape
	a sh:NodeShape ;
	sh:targetClass ex:Company ;
	sh:property ex:CompanyShape-hasDirector .

ex:CompanyShape-hasDirector
    a sh:PropertyShape ;
    sh:path ex:hasDirector ;
    sh:datatype xsd:boolean ;
    sh:maxCount 1 ;
    sh:name "has director" ;
    sh:values [
        shnex:conformsToShape ( [ shnex:var "focusNode" ] ex:HasDirectorShape )
    ] .
							
```

For the following data graph, the value of `ex:hasDirector` is `false`
because `ex:MyCompany` lacks a value for `ex:director`.

```
ex:MyCompany
    a ex:Company .
							
```

## 5. SPARQL Functions

This section introduces SHACL SPARQL function expressions based on sparql12-query that can be used in node expressions.

A blank node that uses a SPARQL function URI `sparql:<NAME>`
as its predicate with an `rdf:List` of arguments as its object
is called a SHACL SPARQL function expression with the corresponding SPARQL function name.

The evaluation follows the SPARQL semantics for the corresponding SPARQL function.
Each item in the `rdf:List` is evaluated as a node expression to produce argument values,
which are then passed to the SPARQL function implementation.
If the SPARQL function produces a single result value, it is wrapped as a singleton list containing that output node.
If the SPARQL function produces no result or an error, the expression produces an empty list or an evaluation failure, respectively.

## 6. Custom Node Expressions

SHACL includes vocabulary terms that can be used to define new node expression functions
by wrapping other (parameterized) node expressions.
This makes it possible to extend the library of available SHACL node expressions without having to
hard-code changes to an engine.

### 6.1 Custom Named Parameter Functions

A custom named parameter function is an IRI in a shapes graph
that is a SHACL instance of `sh:NamedParameterExpressionFunction` and
a SHACL subclass of `sh:NamedParameterExpression`.
It has a single value for `sh:bodyExpression` that is a well-formed
node expression.
  
  
A custom named parameter function declares one or more parameters as values
of `sh:parameter`, where each such parameter has exactly one value for
`sh:path` and that value is an IRI.
At least one of the parameters has `sh:keyParameter true`, declaring the key parameters
for the function.
The key parameters of all node expression functions
(including the built-in ones from the `shnex:` namespace) must be disjoint.
  
  
Custom named parameter functions can reference the declared parameters using an
arg expression such as `[ shnex:arg ex:param ]`, where the value of `shnex:arg`
matches the IRI of the parameter's `sh:path`.

A custom named parameter expression is a node expression
represented by a blank node that has exactly one value for at least one of
the key parameters.

Let `expr` be a custom named parameter expression with the
custom named parameter function `f`.
Let `body` be the value of `sh:bodyExpression` at `f`
in the shapes graph.
  
  
Let `argScope` be a map of (parameter) nodes as keys and (argument) nodes
as values, so that each parameter of `f` has the value of the parameter's
`sh:path` from `expr`.
For example, if `f` declares just one parameter with `sh:path` `ex:param`
and `expr` is `[ ex:param 42 ]` then `argScope` is `{ ex:param : 42 }`.
  
  
The output nodes of `expr` are computed using
`evalExpr(expr, focusGraph, focusNode, scope) -> evalExpr(body, focusGraph, focusNode, argScope)`

*The remainder of this section is non-normative.*

The following example defines a new node expression function `ex:AverageExpression`
that takes another node expression as input using the key parameter `ex:average`
and then calculates the sum of all input nodes and divides it by the number of nodes,
returning the average value of these nodes.

```
ex:AverageExpression
    a sh:NamedParameterExpressionFunction ;
    rdfs:label "Average expression"@en ;
    rdfs:comment "Computes the average of the nodes provided by ex:average." ;
    rdfs:subClassOf sh:NamedParameterExpression ;
    sh:parameter ex:AverageExpression-average ;
    sh:bodyExpression [
        sparql:divide (
            [ shnex:sum [ shnex:arg ex:average ] ]
            [ shnex:count [ shnex:arg ex:average ] ]
        )
    ] ;
.
ex:AverageExpression-average
    a sh:Parameter ;
    sh:path ex:average ;
    sh:name "average" ;
    sh:description "The nodes of which the average shall be computed." ;
    sh:keyParameter true ;
.
						
```

This new node expression function can the be used as follows:

```
ex:CompanyShape-averageIncome
    a sh:PropertyShape ;
    sh:path ex:averageIncome ;
    sh:datatype xsd:decimal ;
    sh:values [
        ex:average [
            shnex:pathValues ( ex:employee ex:income )
        ]
    ] .
						
```

### 6.2 Custom List Parameter Functions

A custom list parameter function is an IRI in a shapes graph
that is a SHACL instance of `sh:ListParameterExpressionFunction` and
a SHACL subclass of `sh:ListParameterExpression`.
The IRI of a custom list parameter function is its list parameter property.
It has a single value for `sh:bodyExpression` that is a well-formed
node expression.
  
  
Custom list parameter functions can reference the arguments using an
arg expression such as `[ shnex:arg 0 ]` and `[ shnex:arg 1 ]`
where the `xsd:integer` `n` corresponds to the `n`th member
of the arguments list, starting with `0` as the first member.
  
  
Custom list parameter functions MAY document the expected shape of the arguments
with values of `sh:parameter` where the values of `sh:path` are
the values `shnex:arg0`, `shnex:arg1` etc.

A custom list parameter expression is a node expression
represented by a blank node that is the subject of exactly one triple
and the predicate of that triple is the list parameter property of a
custom list parameter function in the shapes graph.

Let `expr` be a custom list parameter expression with the
custom list parameter function `f`.
Let `body` be the value of `sh:bodyExpression` at `f`
in the shapes graph.
  
  
Let `argScope` be a map of (parameter index) nodes as keys and (argument) nodes
as values, so that each list argument of `expr` has the index of the argument as an
`xsd:integer` as key, starting with `0` for the first argument.
For example, if `expr` has arguments `( 38 4 )` then the
`argScope` is `{ 0 : 38, 1 : 4 }`.
  
  
The output nodes of `expr` are computed using
`evalExpr(expr, focusGraph, focusNode, scope) -> evalExpr(body, focusGraph, focusNode, argScope)`
where an evaluation failure is reported when there is more than 1 output node.

*The remainder of this section is non-normative.*

The following example defines a new node expression function `ex:spacedConcat`
that takes two nodes as input and returns a string concatenating the two nodes with a space in between.

```
ex:spacedConcat
    a sh:ListParameterExpressionFunction ;
    rdfs:label "Spaced concat expression"@en ;
    rdfs:subClassOf sh:ListParameterExpression ;
    sh:bodyExpression [
        sparql:concat (
            [ shnex:arg 0 ]
            " "
            [ shnex:arg 1 ]
        )
    ] ;
	sh:parameter [
		a sh:Parameter ;
		sh:path shnex:arg0 ;
		sh:name "first string" ;
		sh:description "The first string to concatenate." ;
		sh:datatype xsd:string ;
	] ;
	sh:parameter [
		a sh:Parameter ;
		sh:path shnex:arg1 ;
		sh:name "second string" ;
		sh:description "The second string to concatenate." ;
		sh:datatype xsd:string ;
	] .
						
```

This new node expression function can the be used as follows:

```
ex:Person-fullName
    a sh:PropertyShape ;
    sh:path ex:fullName ;
    sh:datatype xsd:string ;
    sh:values [
        ex:spacedConcat (
            [ shnex:pathValues ex:firstName ]
            [ shnex:pathValues ex:lastName ]
        )
    ] .
						
```

More examples of using custom list parameter functions can be found in
the SHACL-SPARQL spec.

### 6.3 Arg Expressions

Custom node expressions can use `shnex:arg` to access the arguments.

A blank node that is the subject of the following properties
is called an arg expression with the function name `shnex:ArgExpression`:

| Property | Constraints | Description |
| --- | --- | --- |
| **`shnex:arg`** | `sh:or (    [ sh:nodeKind sh:IRI ]    [ sh:datatype xsd:integer ]  )` | The argument key, e.g. `ex:myParameter` or `1`. |

Let `arg` be the value of `shnex:arg` in the arg expression.
The output nodes of the var expression are computed as follows, in order:

1. if `arg` is in the `scope` and has the value `a` then
   `evalExpr(expr, focusGraph, focusNode, scope) -> evalExpr(a, focusGraph, focusNode, {})`
2. otherwise `evalExpr(expr, focusGraph, focusNode, scope) -> []`

*The remainder of this section is non-normative.*

Both `shnex:arg` and `shnex:var` access values from the scope.
The difference is that `shnex:arg` interprets the values as node expressions, while
`shnex:var` treats the values as individual nodes.
As a result, a custom node expression can evaluate nested node expressions that are passed in as arguments.

Examples of `shnex:arg` can be found in
 and .

## 7. Constraint Components

This section introduces SHACL constraint components that operate on node expressions.

### 7.1 sh:expression

Based on node expressions, this section introduces a constraint component called
expression constraints.
Expression constraints can be used in any shape to declare the condition that the
node expression specified via `sh:expression` has `true` as its only output node.
The evaluation of these node expressions is repeated for all value nodes of the shape
as the focus node.

Constraint Component IRI: `sh:ExpressionConstraintComponent`

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:expression` | The node expression that must return `true`. The values of `sh:expression` at a shape must be well-formed node expressions. |

Let `$expr` be a value of `sh:expression`.
For each value node `v`
where `evalExpr(expr, data graph, focusNode, {value: v})`
does not return the list consisting of exactly `true` as its output nodes,
there is a validation result that has `v` as its `sh:value`
and a deep copy of `$expr` in the results graph as its `sh:sourceConstraint`.

*The remainder of this section is non-normative.*

Note that the `scope` in the evaluation of expression constraints maps
`value` to the current value node.

The following example uses some SPARQL-based node expressions to declare
the constraint that the values of `ex:ibanNumber` must start with the same two (upper-case) letters as
the values of the path `ex:country/ex:code`.

```
ex:AccountShape
    a sh:NodeShape ;
    sh:targetClass ex:Account ;
    sh:property ex:AccountShape-ibanNumber .

ex:AccountShape-ibanNumber
    a sh:PropertyShape ;
    sh:path ex:ibanNumber ;
    sh:datatype xsd:string ;
    sh:message "IBAN numbers must start with the country code, in upper-case letters." ;
    sh:expression [
        sparql:strstarts (
            [ shnex:var "value" ]
            [
                sparql:ucase (
                    [
                        shnex:pathValues ( ex:country ex:code )
                        shnex:nodes [ shnex:var "focusNode" ]
                    ]
                )
            ]
        )
    ] .
						
```

```
ex:ValidGermanAccount
    a ex:Account ;
    ex:ibanNumber "DE123456..." ;
    ex:country ex:Germany .

ex:InvalidGermanAccount
    a ex:Account ;
    ex:ibanNumber "DE987654..." ;
    ex:country ex:Estonia .

ex:Estonia
    a ex:Country ;
    ex:code "ee" .

ex:Germany
    a ex:Country ;
    ex:code "de" .
						
```

### 7.2 sh:nodeByExpression

`sh:nodeByExpression` specifies the condition that each value node conforms to the
node shapes produced by a node expression.
The evaluation of these node expressions is repeated for all value nodes of the shape
as the focus node.

Constraint Component IRI: `sh:NodeByExpressionConstraintComponent`

Parameters:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:nodeByExpression` | The node shapes that all value nodes need to conform to. The values of `sh:nodeByExpression` in a shape must be well-formed node expressions. |

Let `$expr` be a value of `sh:nodeByExpression`.
For each value node `v`: perform a conformance check of
`v` against each output node of `evalExpr(expr,
data graph, v, {})` `s`. A failure
MUST be produced if the conformance check of `v` against
`s` produces a failure. Otherwise, if `v` does
not conform to `s`, there is a validation result
with `v` as `sh:value` and a deep copy of
`s` as `sh:sourceConstraint`.

*The remainder of this section is non-normative.*

`sh:nodeByExpression` functions similarly to `sh:node`, but instead of referencing a fixed node shape,
a referenced node expression is used to dynamically compute the set of node shapes to which each value node must conform.

There are three key differences between `sh:nodeByExpression` and `sh:node`:

1. `sh:nodeByExpression` references a node expression instead of a fixed node shape as `sh:node` does.
2. `sh:nodeByExpression` cannot reference a node shape that is a blank node as a value like `sh:node` can,
   as a blank node would be interpreted as a node expression.
3. Results generated by `sh:nodeByExpression` additionally include a value for `sh:sourceConstraint`.

Note that `sh:node` and `sh:nodeByExpression` exhibit the same behavior when given a value that is an IRI of a node shape.
In this case, `sh:node` directly validates against the specified node shape, whereas `sh:nodeByExpression` interprets the IRI
as an IRI expression that evaluates to a set containing the same node shape.

The following example demonstrates how `sh:nodeByExpression` could be used in the context of the [W3C Data Cube Vocabulary](https://www.w3.org/TR/vocab-data-cube/).
Building upon examples 5 and 6 from the Data Cube Vocabulary documentation, Data Structure Definition is extended with the property `eg:hasShape`,
which links to an associated node shape to which relevant `qb:Observation` instances must conform.
To validate that every `qb:Observation` instance conforms to the appropriate shape, `sh:nodeByExpression` with a path values expression
is used to locate the shape at the property path `qb:dataSet/qb:structure/eg:hasShape` from each `qb:Observation` instance.

```
eg:dsd1-shape
	a sh:NodeShape ;
	sh:property [  # _:b1
		sh:path sdmx-dimension:refTime ;
		sh:datatype xsd:date ;
		sh:minCount 1 ;
		sh:maxCount 1 ;
	] ;
	sh:property [  # _:b2
		sh:path eg-measure:quantity ;
		sh:datatype xsd:integer ;
		sh:minCount 1 ;
		sh:maxCount 1 ;
		sh:minInclusive 0 ;
	] ;
	sh:property [  # _:b3
		sh:path eg-measure:weight ;
		sh:datatype xsd:decimal ;
		sh:minCount 1 ;
		sh:maxCount 1 ;
		sh:minInclusive 0.0 ;
	] .

eg:ObservationShape
	a sh:NodeShape ;
	sh:targetClass qb:Observation ;
	sh:nodeByExpression [
		shnex:pathValues (qb:dataSet qb:structure eg:hasShape) ;
	] .
						
```

```
eg:dataset1
	a qb:DataSet ;
	qb:structure eg:dsd1 .

eg:dsd1
	a qb:DataStructureDefinition ;
	rdfs:comment "shipments by time (multiple measures approach)"@en ;
	eg:hasShape eg:dsd1-shape ;
	qb:component [
		qb:dimension sdmx-dimension:refTime;
	] ;
	qb:component [
		qb:measure eg-measure:quantity ;
	] ;
	qb:component [
		qb:measure eg-measure:weight ;
	] .

eg:obs1a
	a qb:Observation;
	qb:dataSet eg:dataset1;
	sdmx-dimension:refTime "2010-07-30"^^xsd:date;
	eg-measure:weight 1.3 ;
	eg-measure:quantity 42 .

eg:obs1b
	a qb:Observation;
	qb:dataSet eg:dataset1;
	sdmx-dimension:refTime "2010-07-31T12:00:00"^^xsd:dateTime;
	eg-measure:weight 1.4 .
						
```

```
[	a sh:ValidationReport ;
	sh:conforms false ;
	sh:result [
		a sh:ValidationResult ;
		sh:resultSeverity sh:Violation ;
		sh:focusNode eg:obs1b;
		sh:value eg:obs1b ;
		sh:resultMessage "Value does not conform to shape eg:dsd1-shape." ;
		sh:sourceConstraint eg:dsd1-shape ;
		sh:sourceConstraintComponent sh:NodeByExpressionConstraintComponent ;
		sh:sourceShape eg:ObservationShape ;
		sh:detail [
			a sh:ValidationResult ;
			sh:resultSeverity sh:Violation ;
			sh:focusNode eg:obs1b ;
			sh:resultPath sdmx-dimension:refTime ;
			sh:value "2010-07-31T12:00:00"^^xsd:dateTime ;
			sh:resultMessage "Value does not have datatype xsd:date" ;
			sh:sourceConstraintComponent sh:DatatypeConstraintComponent ;
			sh:sourceShape _:b1 ;
		] ;
		sh:detail [
			a sh:ValidationResult ;
			sh:resultSeverity sh:Violation ;
			sh:focusNode eg:obs1b ;
			sh:resultPath eg-measure:quantity ;
			sh:resultMessage "Less than 1 values" ;
			sh:sourceConstraintComponent sh:MinCountConstraintComponent ;
			sh:sourceShape _:b2 ;
		] ;
	] ;
] .
						
```

## 8. Dynamic SHACL

This section defines Dynamic SHACL as a dialect of SHACL that some implementations MAY support.

In Dynamic SHACL any parameter of a constraint can be computed using a node expression,
excluding those that do *not* allow blank nodes (such as `sh:node`)
but including those that take SHACL lists as values (such as `sh:class`,
`sh:datatype`, and `sh:in`).
During validation, such node expressions are evaluated in the data graph,
using the current focus node.
The resulting nodes will be used as parameters for the constraint.

### 8.1 Example: Dynamic Minimum Age of Presidents

As a use case of Dynamic SHACL, assume we want to express that the legal minimum age
of a president is 18 unless the country is USA, where it is 35.

**Example: Example of Dynamic SHACL using a node expression at sh:minInclusive**

```
ex:PresidentShape
    a sh:NodeShape ;
	sh:targetClass ex:President ;
    sh:property ex:PresidentShape-age ;
.
ex:PresidentShape-age
    a sh:PropertyShape ;
    sh:path ex:age ;
    sh:minInclusive [
        shnex:if [
            sparql:eq (
                [ shnex:pathValues ex:country ]
                ex:USA
            )
        ] ;
        shnex:then 35 ;
        shnex:else 18 ;
    ] .
						
```

### 8.2 Example: Dynamic Enumerations

As a use case of Dynamic SHACL, assume the following data graph.

**Example: Example data graph with addresses**

```
ex:ArizonaAddress1
    a ex:Address ;
    ex:street "123 John Muir Ave" ;
    ex:country ex:USA ;
    ex:state "AZ" ;
.
ex:QueenslandAddress1
    a ex:Address ;
    ex:street "123 Bob Katter Cl" ;
    ex:country ex:Australia ;
    ex:state "QLD" ;
.
						
```

We want to express that the valid values of `ex:state` depend on the value of `ex:country`
at the given focus node.
For example, the valid values for country `ex:USA` would be `( "AL" "AK" "AZ" ... )`
while valid values for country `ex:Australia` would be `( "ACT" "NSW" "NT" "QLD" "SA" "TAS" "VIC" "WA" )`.
This fact can be represented as part of the data:

**Example: The valid states can be attached to each country**

```
ex:Australia
    a            ex:Country ;
    ex:stateCode "ACT",
                 "NSW",
                 "NT",
                 "QLD",
                 "SA",
                 "TAS",
                 "VIC",
                 "WA" ;
.
ex:USA
    a            ex:Country ;
    ex:stateCode "AL",
                 "AK",
                 "AZ",
                 "AR" ; # ...
.
						
```

Using this extra information, we can now define a `sh:in` constraint using a path values expression:

**Example: Example of Dynamic SHACL using a node expression at sh:in**

```
ex:Address
    a sh:ShapeClass ;
    sh:property ex:Address-state ;
.
ex:Address-state
    a sh:PropertyShape ;
    sh:path ex:state ;
    sh:in [
        shnex:pathValues ( ex:country ex:stateCode )
    ] .
						
```

During validation, a Dynamic SHACL engine will evaluate the path values expression at `sh:in`
and use the resulting nodes as members of the allowed values.
Thus, when the value of `ex:country` is `ex:USA`, it will look up the
state codes that are linked to `ex:USA`.

## 9. Security and Privacy Considerations

Security considerations of SHACL Node Expressions include all the
security considerations of SHACL Core.

## A. Acknowledgements

Many people contributed to this document, including members of the RDF Data Shapes Working Group.
