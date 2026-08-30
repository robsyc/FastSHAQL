<!-- https://w3c.github.io/data-shapes/shacl12-sparql/ — W3C editors' draft, fetched 2026-08-31 -->

This document defines SPARQL-related extensions of the SHACL Shapes Constraint Language.
While the Core part of SHACL defines the basic syntax of shapes and the most common constraint components
supported by SHACL, the SPARQL-related extensions cover features that extend the expressiveness of Core
by means of SPARQL.
In particular, this document defines how constraints and constraint components can be defined using SPARQL.
Furthermore, this document introduces SPARQL-based node expressions that can be used to derive lists of nodes.
Finally, this document defines a declarative mechanism to define new SPARQL functions based on SHACL node expressions.

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

This document specifies the SPARQL-related features of the Shapes Constraint Language (SHACL).

### 1.1 Terminology

Throughout this document, the following terminology is used.

The SHACL SPARQL Extensions defined in this document are sometimes called SHACL-SPARQL.

Terminology that is linked to portions of RDF 1.2 Concepts and Abstract Syntax is used in SHACL-SPARQL as defined there.
Terminology that is linked to portions of SPARQL 1.2 Query Language is used in SHACL-SPARQL as defined there.
Terminology that is linked to portions of SHACL 1.2 Core is used in SHACL-SPARQL as defined there.
A single linkage is sufficient to provide a definition for all occurrences of a particular term in this document.

Definitions are complete within this document, i.e., if there is no rule to
make some situation true in this document then the situation is false.

This document uses the terms
RDF graph,
RDF triple,
IRI,
literal,
blank node,
node of an RDF graph,
datatype,
reifier,
RDF term, and
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
SPARQL property path,
data graph,
shapes graph,
target,
validator,
node expression,
node expression function,
function name,
output nodes,
focus graph,
conform,
failure,
validation result,
SHACL instance,
SHACL subclass,
SHACL superclass,
SHACL type,
well-formed,
ill-formed,
as defined in the SHACL 1.2 Core specification shacl12-core.

A binding is a pair (variable, RDF term), consistent with the term's use in sparql12-query.
A solution is a set of bindings where each variable must be unique.
Informally, a solution is often understood as one row in the body of the result table of a SPARQL query.

### 1.2 Document Conventions

The syntax of SHACL is RDF.
The examples in this document use Turtle rdf12-turtle.
Other RDF serializations such as RDF/XML may be used in practice.
The reader should be familiar with basic RDF concepts rdf12-concepts such as triples and with SPARQL sparql12-query.

Within this document, the following namespace prefix bindings are used:

| Prefix | Namespace |
| --- | --- |
| `owl:` | `http://www.w3.org/2002/07/owl#` |
| `rdf:` | `http://www.w3.org/1999/02/22-rdf-syntax-ns#` |
| `rdfs:` | `http://www.w3.org/2000/01/rdf-schema#` |
| `sh:` | `http://www.w3.org/ns/shacl#` |
| `xsd:` | `http://www.w3.org/2001/XMLSchema#` |
| `ex:` | `http://example.com/ns#` |

Within this document, the following JSON-LD context is used:

```
{
  "@context": {
    "owl": "http://www.w3.org/2002/07/owl#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "sh": "http://www.w3.org/ns/shacl#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "ex": "http://example.com/ns#"
  }
}
```

Note that the URI of the graph defining the SHACL vocabulary itself is equivalent to
the namespace above, i.e. it includes the `#`.
References to the SHACL vocabulary, e.g. via `owl:imports` should include the `#`.

Throughout the document, color-coded boxes containing RDF graphs in Turtle will appear.
These fragments of Turtle documents use the prefix bindings given above.

```
# This box represents an input shapes graph

<s> ex:p <o> .
					
```

```
# This box represents an input data graph.
					
```

```
# This box represents an output results graph
					
```

SHACL Definitions appear in blue boxes:

```
# This box contains SPARQL or textual definitions.
```

Grey boxes such as this include syntax rules that apply to the shapes graph.

SPARQL variables using the `$` marker represent external bindings that are pre-bound or, in the case of `$PATH`, substituted in the SPARQL query before execution (as explained in [4.3 Validation with SPARQL-based Constraint Components](#constraint-components-validation)).

`true` denotes the RDF term `"true"^^xsd:boolean`.
`false` denotes the RDF term `"false"^^xsd:boolean`.

### 1.3 Conformance

This document defines the **SHACL-SPARQL** language that extends SHACL Core.
This specification describes conformance criteria for:

- **SHACL-SPARQL validation processors** as processors that support SHACL validation using
  [3. SPARQL-based Constraints](#sparql-constraints) and [4. SPARQL-based Constraint Components](#sparql-constraint-components)
- **SPARQL node expression processors** as processors that can evaluate
  [6. SPARQL-based Node Expressions](#sparql-node-expressions)
- **SPARQL custom functions processors** as processors that can evaluate
  [7. Declaring SPARQL Functions based on Node Expressions](#sparql-functions)

Also see the discussion of well-formedness in the Conformance section of SHACL Core.

## 2. Prefix Declarations for SPARQL Queries

This section introduces the mechanisms that are used throughout this document to declare namespace prefixes
for SPARQL queries.

A shapes graph may include declarations of namespace prefixes so that these prefixes can be used to abbreviate the SPARQL queries derived from the same shapes graph.
The syntax of such prefix declarations is illustrated by the following example.

```
ex:
	sh:declare [
		sh:prefix "ex" ;
		sh:namespace "http://example.com/ns#"^^xsd:anyURI ;
	] ;
	sh:declare [
		sh:prefix "schema" ;
		sh:namespace "http://schema.org/" ;
	] ;
	a sh:ShapesGraph ;    # Optional
	owl:imports sh: .   # Optional
					
```

IRIs or blank nodes that have values for both `sh:prefix` and `sh:namespace`
are called prefix declarations.
The SHACL vocabulary includes the class `sh:PrefixDeclaration` as type for such prefix declarations
although no `rdf:type` triple is required for them.
Prefix declarations have exactly one value for the property `sh:prefix`.
The values of `sh:prefix` are literals of datatype `xsd:string`.
Prefix declarations have exactly one value for the property `sh:namespace`.
The values of `sh:namespace` are literals of datatype `xsd:anyURI` or `xsd:string`.
Such a pair of values specifies a single mapping of a prefix to a namespace.
The values of the property `sh:declare` are prefix declarations.

The recommended subject for values of `sh:declare` is the IRI of the named graph containing the shapes that use the prefixes.
These IRIs are often declared as an instance of `sh:ShapesGraph` or `owl:Ontology`, but this is not required.

Among others, Prefix declarations can be used by SPARQL-based constraints,
the validators of [SPARQL-based constraint components](#sparql-constraint-components),
[SPARQL-based node expressions](#sparql-node-expressions), and
SPARQL-based inference rules.
These nodes can use the property `sh:prefixes` to specify a set of prefix mappings.
An example use of the `sh:prefixes` property can be found in this
[example](#sparql-constraints-example).

The values of `sh:prefixes` are either IRIs or blank nodes.
A SHACL processor collects a set of prefix mappings as the union of all
individual prefix mappings that are values of the SPARQL property path `sh:prefixes/(^owl:versionIRI?/owl:imports)*/sh:declare`
of the SPARQL-based constraint or validator.
The `^owl:versionIRI?` element supports graphs that are imported by
`owl:versionIRI`,
navigating from the version IRI to the shapes graph IRI before following further `owl:imports`.
If such a collection of prefix declarations contains multiple different namespaces for the same value of `sh:prefix`,
then the shapes graph is ill-formed.
(Note that SHACL processors MAY ignore prefix declarations that are never reached).

If a SPARQL query has no value for `sh:prefixes` then the system will use those prefix declarations
from the shapes graph that are values of `sh:declare` at a SHACL instance of
`owl:Ontology`, `sh:DataGraph`, `sh:ShapesGraph`,
or `sh:RulesGraph` (which is a subclass of `sh:ShapesGraph`).

A SHACL processor transforms the values of `sh:select` (and similar properties such as `sh:ask` and `sh:construct`)
into SPARQL by prepending `PREFIX` declarations
for all prefix mappings.
Each value of `sh:prefix` is turned into the `PNAME_NS`, while each value of `sh:namespace` is turned
into the `IRIREF` in the `PREFIX` declaration.
For the example shapes graph above, a SHACL-SPARQL processor would produce lines such as `PREFIX ex: <http://example.com/ns#>`.
The SHACL-SPARQL processor MUST produce a failure if the resulting query string cannot be parsed into a valid SPARQL 1.2 query.

In the rest of this document, the `sh:prefixes` statements may have been omitted for brevity.

## 3. SPARQL-based Constraints

SHACL-SPARQL supports a constraint component that can be used to express restrictions based on a SPARQL SELECT query.

Constraint Component IRI: `sh:SPARQLConstraintComponent`

Parameters:

| Property | Summary |
| --- | --- |
| `sh:sparql` | A SPARQL-based constraint declaring the SPARQL query to evaluate. |

The [syntax rules](#sparql-constraints-syntax) and [validation process](#sparql-constraints-validation) for SPARQL-based constraints are defined in the rest of this section.

### 3.1 An Example SPARQL-based Constraint

The following example illustrates the syntax of a SPARQL-based constraint.

**Example: A SPARQL-based constraint**

```
ex:LanguageExampleShape
	a sh:NodeShape ;
	sh:targetClass ex:Country ;
	sh:sparql [
		a sh:SPARQLConstraint ;   # This triple is optional
		sh:message "Values are literals with German language tag." ;
		sh:prefixes ex: ;
		sh:select """
			SELECT $this (ex:germanLabel AS ?path) ?value
			WHERE {
				$this ex:germanLabel ?value .
				FILTER (!isLiteral(?value) || !langMatches(lang(?value), "de"))
			}
			""" ;
	] .

ex:
	sh:declare [] .   # See prefix declarations
```

The target of the shape above includes all SHACL instances of `ex:Country`.
For those nodes (represented by the variable `this`), the SPARQL query walks through the values of `ex:germanLabel`
and verifies that they are literals with a German language code.

```
ex:ValidCountry a ex:Country ;
	ex:germanLabel "Spanien"@de .

ex:InvalidCountry a ex:Country ;
	ex:germanLabel "Spain"@en .
						
```

```
[	a sh:ValidationReport ;
	sh:conforms false ;
	sh:result [
		a sh:ValidationResult ;
		sh:resultSeverity sh:Violation ;
		sh:focusNode ex:InvalidCountry ;
		sh:resultPath ex:germanLabel ;
		sh:value "Spain"@en ;
		sh:sourceConstraintComponent sh:SPARQLConstraintComponent ;
		sh:sourceShape ex:LanguageExampleShape ;
		# ...
	]
] .
						
```

The SPARQL query returns result set solutions for all bindings of the variable `value` that violate the constraint.
There is a validation result for each solution in that result set, applying the [mapping rules](#sparql-constraints-validation) explained later.
In this example, each validation result will have the binding for the variable `this` as the `sh:focusNode`,
`ex:germanLabel` as `sh:resultPath` and the violating value as `sh:value`.

The following example illustrates a similar scenario as above, but with a property shape.

```
ex:LanguageExamplePropertyShape
	a sh:PropertyShape ;
	sh:targetClass ex:Country ;
	sh:path ex:germanLabel ;
	sh:sparql [
		a sh:SPARQLConstraint ;   # This triple is optional
		sh:message "Values are literals with German language tag." ;
		sh:prefixes ex: ;
		sh:select """
			SELECT $this ?value
			WHERE {
				$this $PATH ?value .
				FILTER (!isLiteral(?value) || !langMatches(lang(?value), "de"))
			}
			""" ;
	] .

ex:
	sh:declare [] .   # See prefix declarations
```

### 3.2 Syntax of SPARQL-based Constraints

Shapes may have values for the property `sh:sparql`, and these values are either IRIs or blank nodes.
These values are called SPARQL-based constraints.

SPARQL-based constraints have exactly one value for the property `sh:select`.
The value of `sh:select` is a literal of datatype `xsd:string`.
The class `sh:SPARQLConstraint` is defined in the SHACL vocabulary and may be used as the type of these constraints (although no type is required).
Using the [prefix handling rules](#sparql-prefixes), the value of `sh:select` is a valid SPARQL 1.2 SELECT query.
The SPARQL query derived from the value of `sh:select` projects the variable `this` in the SELECT clause.

The following two properties are similar to their use in shapes:

SPARQL-based constraints may have values for the property `sh:message`
and these are literals with datatype `xsd:string`, `rdf:dirLangString`, `rdf:langString`, or `rdf:HTML`.
There should neither be more than one value for `sh:message` with the same language tag, nor multiple values with datatype `xsd:string`.
SPARQL-based constraints may have at most one value for the property `sh:deactivated`
and this value is either `true` or `false`.
SPARQL-based constraints may have at most one value for the property `sh:severity`
and this value is an IRI.

SELECT queries used in the context of property shapes use a special variable named `PATH` as a placeholder for the path used by the shape.

The only legal use of the variable `PATH` in the SPARQL queries of SPARQL-based constraints
and SELECT-based validators is in the
predicate position of a triple pattern.
A query that uses the variable `PATH` in any other position is ill-formed.

### 3.3 Validation with SPARQL-based Constraints

This section explains the validator of `sh:SPARQLConstraintComponent`.
Note that this validator only explains one possible implementation strategy, and
SHACL processors may choose alternative approaches as long as the outcome is equivalent.

Let `$sparql` be a value of `sh:sparql`.
There are no validation results if the SPARQL-based constraint has `true`
as a value for the property `sh:deactivated`.
Otherwise, execute the SPARQL query specified by the SPARQL-based constraint `$sparql`
pre-binding the variable `this` as described in [3.3.1 Pre-bound variable $this in SPARQL Constraints](#sparql-constraints-prebound).
If the shape is a property shape, then prior to execution
substitute the variable `PATH` where it appears in the predicate
position of a triple pattern
with a valid SPARQL surface syntax string of the SHACL property path
specified via `sh:path` at the property shape.
There is one validation result for each solution that does not have `true` as the binding for the variable `failure`.
These validation results MUST have the property values explained in [3.3.2 Mapping of Solution Bindings to Result Properties](#sparql-constraints-variables).
If `$sparql` has a value for `sh:severity` then the validation result MUST
have that value as its (only) `sh:resultSeverity`.
A failure MUST be produced if and only if one of the solutions has `true` as the binding for `failure`.

#### 3.3.1 Pre-bound variable $this in SPARQL Constraints

When the SPARQL queries of SPARQL-based constraints and the validators
of SPARQL-based constraint components are processed,
the SHACL-SPARQL processor pre-binds values for the variable `$this`
to the current focus node.

#### 3.3.2 Mapping of Solution Bindings to Result Properties

The property values of the validation result nodes are derived by the following rules, through a combination of result solutions and the values of the constraint itself.
The rules are meant to be executed from top to bottom, so that the first bound value will be used.

| Property | Production Rules |
| --- | --- |
| `sh:focusNode` | 1. The binding for the variable `this` |
| `sh:resultPath` | 1. The binding for the variable `path`, if that is a IRI 2. For results produced by a property shape, a SHACL property path that is equivalent to the value of `sh:path` of the shape |
| `sh:value` | 1. The binding for the variable `value` 2. The value node |
| `sh:resultMessage` | 1. The binding for the variable `message` 2. For SPARQL-based constraints: The values of `sh:message` of the SPARQL-based constraint.    For SPARQL-based constraint components: The values of `sh:message` of the validator of the SPARQL-based constraint component. 3. For SPARQL-based constraint components: The values of `sh:message` of the SPARQL-based constraint component. 4. The default mechanisms for declaring messages at the shape or constraint apply otherwise.   These message literals may include the names of any SELECT result variables via `{?varName}` or `{$varName}`. If the constraint is based on a [SPARQL-based constraint component](#sparql-constraint-components), then the component's parameter names can also be used. These `{?varName}` and `{$varName}` blocks SHOULD be replaced with suitable string representations of the values of said variables. |
| `sh:sourceConstraint` | 1. The SPARQL-based constraint, i.e. the value of `sh:sparql` |

## 4. SPARQL-based Constraint Components

SPARQL-based constraints provide a lot of flexibility
but may be hard to understand for some people or lead to repetition.
This section introduces SPARQL-based constraint components as a way to abstract the complexity of SPARQL
and to declare high-level reusable components similar to the Core constraint components.
Such constraint components can be declared using the SHACL RDF vocabulary and thus shared and reused.

### 4.1 An Example SPARQL-based Constraint Component

The following example demonstrates how SPARQL can be used to specify new constraint components using the SHACL-SPARQL language.
The example implements `sh:pattern` and `sh:flags` using a
[SPARQL ASK](#SPARQLAskValidator) query to validate that each value node matches a given regular expression.
Note that this is only an example implementation and should not be considered normative.

**Example: Constraint component based on SPARQL**

```
sh:PatternConstraintComponent
	a sh:ConstraintComponent ;
	sh:parameter [
		sh:path sh:pattern ;
	] ;
	sh:parameter [
		sh:path sh:flags ;
		sh:optional true ;
	] ;
	sh:validator ex:hasPattern .

ex:hasPattern
	a sh:SPARQLAskValidator ;
	sh:message "Value does not match pattern {$pattern}" ;
	sh:ask """
		ASK {
			FILTER (!isBlank($value) &&
				IF(bound($flags), regex(str($value), $pattern, $flags), regex(str($value), $pattern)))
		}""" .
						
```

Once the constraint component has been declared, its parameters can be used in a shape as illustrated in the following example.

**Example: Constraint component based on SPARQL**

```
ex:CaseInsensitiveSearch
    a sh:NodeShape ;
    sh:property [
    sh:path ex:code ;
    sh:pattern "^[A-Z]{3}[0-9]{2}$" ;
    sh:flags "i" ;   # case-insensitive match
  ] .
						
```

Constraint components provide instructions to validation engines on how to identify and validate constraints within a shape.
In general, if a shape `S` has a value for a property `p`, and there is a constraint component
`C` that specifies `p` as a parameter, and `S` has values for all mandatory parameters of `C`,
then the set of these parameter values (including the optional parameters) declare a constraint and the validation engine uses a suitable validator from `C`
to perform the validation of this constraint.
In the example above, `sh:PatternConstraintComponent` declares the mandatory parameter `sh:pattern`,
the optional parameter `sh:flags`,
and a validator that can be used to perform validation against either node shapes or property shapes.

### 4.2 Syntax of SPARQL-based Constraint Components

A SPARQL-based constraint component is an IRI that has SHACL type
`sh:ConstraintComponent` in the shapes graph.

The mechanism to declare new constraint components in this document is limited to those based on SPARQL.
However, the general syntax of declaring parameters and validators has been designed to also work for other extension languages such as JavaScript.

#### 4.2.1 Parameter Declarations (sh:parameter)

The parameters of a constraint component are declared via the property `sh:parameter`.
The values of `sh:parameter` are called parameter declarations.
The class `sh:Parameter` may be used as type of parameter declarations but no such triple is required.
Each parameter declaration has exactly one value for the property `sh:path`.
At parameter declarations, the value of `sh:path` is an IRI.

The local name of an IRI is defined as the longest NCNAME
at the end of the IRI, not immediately preceded by the first colon in the IRI.
The parameter name of a parameter declaration is defined as the local name of the value of `sh:path`.
To ensure that a correct mapping from parameters into SPARQL variables is possible, the following syntax rules apply:

Every parameter name is a valid SPARQL VARNAME.
Parameter names must not be one of the following: `this`, `path`, `PATH`, `value`.
A constraint component where two or more parameter declarations use the same parameter names is ill-formed.

The values of `sh:optional` must be literals with datatype `xsd:boolean`.
A parameter declaration can have at most one value for the property `sh:optional`.
If set to `true` then the parameter declaration declares an optional parameter.
Every constraint component has at least one non-optional parameter.

The class `sh:Parameter` is defined as a SHACL subclass of `sh:PropertyShape`,
and all properties that are applicable to property shapes may also be used for parameters.
This includes descriptive properties such as `sh:name` and `sh:description`
but also constraint parameters such as `sh:class`.
Shapes that do not conform with the constraints declared for the parameters are ill-formed.
Some implementations MAY use these constraint parameters to prevent the execution of constraint components with invalid parameter values.

#### 4.2.2 Label Templates (sh:labelTemplate)

The property `sh:labelTemplate` can be used at any constraint component to suggest how constraints could be rendered to humans.
The values of `sh:labelTemplate` are strings (possibly with language tag) and
are called label templates.

*The remainder of this section is non-normative.*

Label templates can include the names of the parameters that are declared for the constraint component
using the syntaxes `{?varName}` or `{$varName}`,
where `varName` is the name of the parameter name.
At display time, these `{?varName}` and `{$varName}` blocks should be replaced with the actual parameter values.
There may be multiple label templates for the same subject, but they should not have the same language tags
and there should not be more than one template with datatype `xsd:string`.

#### 4.2.3 Validators

For every supported shape type (i.e., property shape or node shape)
the constraint component declares a suitable validator.
For a given constraint, a validator is selected from the constraint component using the following rules, in order:

1. For node shapes, use one of the values of `sh:nodeValidator`, if present.
2. For property shapes, use one of the values of `sh:propertyValidator`, if present.
3. Otherwise, use one of the values of `sh:validator`.

If no suitable validator can be found, a SHACL-SPARQL processor ignores the constraint.

SHACL-SPARQL includes two types of validators, based on [SPARQL SELECT](#SPARQLSelectValidator) (for `sh:nodeValidator` and `sh:propertyValidator`)
or [SPARQL ASK](#SPARQLAskValidator) queries (for `sh:validator`).

##### 4.2.3.1 SELECT-based Validators

Validators with SHACL type `sh:SPARQLSelectValidator` are called SELECT-based validators.
The values of `sh:nodeValidator` must be SELECT-based validators.
The values of `sh:propertyValidator` must be SELECT-based validators.
SELECT-based validators have exactly one value for the property `sh:select`.
The value of `sh:select` is a valid SPARQL 1.2 SELECT query using the aforementioned [prefix handling rules](#sparql-prefixes).
The SPARQL query derived from the value of `sh:select` projects the variable `this` in its SELECT clause.

*The remainder of this section is non-normative.*

The following example illustrates the declaration of a constraint component based on a SPARQL SELECT query.
It is a generalized variation of the example from [3.1 An Example SPARQL-based Constraint](#sparql-constraints-example).
Where that SPARQL query included two constants: the specific property `ex:germanLabel` and the language tag `de`,
this example generalizes the constraint so that any property can be defined with a language tag. In practice, the constraint component is applied
by adding the parameter predicate(s) to a shape (e.g., ex:lang "de"), which a SHACL-SPARQL processor pre-binds to the corresponding SPARQL
variable(s) (e.g., `$lang`) before executing the SELECT validator.
Constraint components make it possible to generalize such scenarios, so that constants get pre-bound with parameters.
This allows the query logic to be reused in multiple places, without having to write any new SPARQL.

**Example: Constraint component based on SPARQL**

```
ex:LanguageConstraintComponentUsingSELECT
	a sh:ConstraintComponent ;
	rdfs:label "Language constraint component" ;
	sh:parameter [
		sh:path ex:lang ;
		sh:datatype xsd:string ;
		sh:minLength 2 ;
		sh:name "language" ;
		sh:description "The language tag, e.g. \"de\"." ;
	] ;
	sh:labelTemplate "Values are literals with language \"{$lang}\"" ;
	sh:propertyValidator [
		a sh:SPARQLSelectValidator ;
		sh:message "Values are literals with language \"{?lang}\"" ;
		sh:select """
			SELECT DISTINCT $this ?value
			WHERE {
				$this $PATH ?value .
				FILTER (!isLiteral(?value) || !langMatches(lang(?value), $lang))
			}
			"""
	] .
								
```

Once a constraint component has been declared (in a shapes graph), its parameters can be used as illustrated in the following example. Any property shape
that includes `ex:lang` is interpreted as using `ex:LanguageConstraintComponentUsingSELECT` (binding `$lang` to that value).

**Example: Shape declaration using ex:LanguageConstraintComponent**

```
ex:LanguageExampleShape
	a sh:NodeShape ;
	sh:targetClass ex:Country ;
	sh:property [
		sh:path ex:germanLabel ;
		ex:lang "de" ;
	] ;
	sh:property [
		sh:path ex:englishLabel ;
		ex:lang "en" ;
	] .
								
```

The example shape above specifies the condition that all values of `ex:germanLabel` carry the language tag `de`
while all values of `ex:englishLabel` have `en` as their language.
These details are specified via two property shapes that have values for the `ex:lang` parameter required by the constraint component.

##### 4.2.3.2 ASK-based Validators

Many constraint components are of the form in which all value nodes are tested individually against some boolean condition.
Writing SELECT queries for these becomes burdensome, especially if a constraint component can be
used for both property shapes and node shapes.
SHACL-SPARQL provides an alternative, more compact syntax for validators based on ASK queries.

Validators with SHACL type `sh:SPARQLAskValidator` are called ASK-based validators.
The values of `sh:validator` must be ASK-based validators.
ASK-based validators have exactly one value for the property `sh:ask`.
The value of `sh:ask` must be a literal with datatype `xsd:string`.
The value of `sh:ask` must be a valid SPARQL ASK query using the aforementioned [prefix handling rules](#sparql-prefixes).

*The remainder of this section is non-normative.*

The ASK queries return `true` if and only if a given value node
(represented by the pre-bound variable `value`) conforms to the constraint.

The following example declares a constraint component using an ASK query.

**Example: Constraint component based on SPARQL**

```
ex:LanguageConstraintComponentUsingASK
	a sh:ConstraintComponent ;
	rdfs:label "Language constraint component" ;
	sh:parameter [
		sh:path ex:lang ;
		sh:datatype xsd:string ;
		sh:minLength 2 ;
		sh:name "language" ;
		sh:description "The language tag, e.g. \"de\"." ;
	] ;
	sh:labelTemplate "Values are literals with language \"{$lang}\"" ;
	sh:validator ex:hasLang .

ex:hasLang
	a sh:SPARQLAskValidator ;
	sh:message "Values are literals with language \"{$lang}\"" ;
	sh:ask """
		ASK {
			FILTER (isLiteral($value) && langMatches(lang($value), $lang))
		}
		""" .
								
```

Note that the validation condition implemented by an ASK query is "in the inverse direction" from its SELECT counterpart:
ASK queries return `true` for value nodes that conform to the constraint, while SELECT queries return those value nodes that do not conform.

### 4.3 Validation with SPARQL-based Constraint Components

This section defines the validator of SPARQL-based constraint components.
Note that this validator only explains one possible implementation strategy, and
SHACL processors may choose alternative approaches as long as the outcome is equivalent.

As the first step, a validator MUST be selected based on the rules outlined
in [4.2.3 Validators](#constraint-components-validators).
Then the following rules apply, producing a set of solutions of SPARQL queries:

- For ASK-based validators:
  For each value node `v` where the SPARQL ASK query returns `false`
  with `v` pre-bound to the variable `value`,
  create one solution consisting of the bindings
  (`$this`, focus node) and (`$value`, `v`).
  Let `QS` be a list of these solutions.
- For SELECT-based validators:
  If the shape is a property shape, then prior to execution
  substitute the variable `PATH` where it appears in the predicate
  position of a triple pattern
  with a valid SPARQL surface syntax string of the SHACL property path
  specified via `sh:path` at the property shape.
  Let `QS` be the solutions produced by executing the SPARQL query.

The SPARQL query executions above MUST pre-bind the variable
`this` as described in [3.3.1 Pre-bound variable $this in SPARQL Constraints](#sparql-constraints-prebound).
In addition, each value of a parameter of the constraint component in the constraint
MUST be pre-bound as a variable that has the parameter name as its name.

The production rules for the validation results are identical to those for [SPARQL-based constraints](#sparql-constraints-validation-rule),
using the solutions `QS` as produced above.

## 5. Annotation Properties

This section extends the general [mechanism](#sparql-constraints-variables)
to produce validation results using [SPARQL-based constraints](#sparql-constraints) or
[constraint components](#sparql-constraint-components).

Implementations that support this feature make it possible to inject annotation properties
into the validation result nodes created for each solution produced by the `SELECT` queries of a
SPARQL-based constraint or constraint component.
Any such annotation property needs to be declared via a value of `sh:resultAnnotation` at
the subject of the `sh:select` or `sh:ask` triple.

The values of `sh:resultAnnotation` are
called result annotations and are either IRIs or blank nodes.

Result annotations have the following properties:

| Property | Summary and Syntax Rules |
| --- | --- |
| `sh:annotationProperty` | The property that shall be set. Each result annotation has exactly one value for the property `sh:annotationProperty` and this value is an IRI. |
| `sh:annotationVarName` | The name of the SPARQL variable to take the annotation values from. Each result annotation has at most 1 value for the property `sh:annotationVarName` and this value is literal with datatype `xsd:string`. |
| `sh:annotationValue` | Constant RDF terms that shall be used as default values. |

For each solution of a `SELECT` result set, a SHACL processor that supports annotations
walks through the declared result annotations.
The mapping from result annotations to SPARQL variables uses the following rules:

1. Use the value of the property `sh:annotationVarName`
2. If no such value exists, use the local name of the value of `sh:annotationProperty`
   as the variable name.

If a variable name could be determined, then the SHACL processor copies the binding for the given variable
as a value for the property specified using `sh:annotationProperty`
into the validation result that is being produced for the current solution.
If the variable has no binding in the result set solution,
then the values of `sh:annotationValue` are used, if present.

**Example: Example of using result annotations**

```
ex:AnnotationExample
	a sh:NodeShape ;
	sh:targetNode ex:ExampleResource ;
	sh:sparql [   # _:b1
		sh:resultAnnotation [
			sh:annotationProperty ex:time ;
			sh:annotationVarName "time" ;
		] ;
		sh:select """
			SELECT $this ?message ?time
			WHERE {
				BIND (CONCAT("The ", "message.") AS ?message) .
				BIND (NOW() AS ?time) .
			}
			""" ;
	] .
					
```

```
[	a sh:ValidationReport ;
	sh:conforms false ;
	sh:result [
		a sh:ValidationResult ;
		sh:focusNode ex:ExampleResource ;
		sh:resultMessage "The message." ;
		sh:resultSeverity sh:Violation ;
		sh:sourceConstraint _:b1 ;
		sh:sourceConstraintComponent sh:SPARQLConstraintComponent ;
		sh:sourceShape ex:AnnotationExample ;
		ex:time "2015-03-27T10:58:00"^^xsd:dateTime ;  # Example
	]
] .
					
```

## 6. SPARQL-based Node Expressions

This section introduces node expression functions based on SPARQL.

### 6.1 Select Expressions

A node expression that has a value for `sh:select` is called a select expression with the function name
`sh:SelectExpression`.

A node in an RDF graph is a well-formed select expression if it is a blank node
that has exactly one value for the predicate `sh:select`
and this value is a literal with datatype `xsd:string`.
A well-formed select expression can have at most one value for the property
`sh:prefixes` and this value can only be an IRI or a blank node.  
  
Using the [prefix handling rules](#sparql-prefixes), the value of `sh:select` is a valid SPARQL 1.2 SELECT query.
The SPARQL query derived from the value of `sh:select` projects exactly one variable in the SELECT clause.

The output nodes of a select expression are the list `resultNodes` consisting of exactly the bindings of the (only)
variable that is projected from the `SELECT` clause when the query is evaluated against the focus graph.
The value of `focusNode` is pre-bound as the value of the SPARQL variable `this`.
The value of each scope variable is pre-bound as a SPARQL variable with the same name and value.
If the name of a variable in scope is not a string literal, use `"arg" + str(name)`.
For example, if the variable name is `"0"^^xsd:integer`, use `arg0`.
A failure is produced when one of the scope variables is called `this`.
  
  
`evalExpr(expr, focusGraph, focusNode, scope) -> resultNodes`

*The remainder of this section is non-normative.*

**Example: A dynamically computed property using a node expression based on a SPARQL query**

Here is an example use of a select expression, computing the values of a property shape for the property
"full name" as the concatenation of the `ex:firstName`, a space, and the `ex:lastName`.

```
ex:Person-fullName
	a sh:PropertyShape ;
	sh:name "full name" ;
	sh:path ex:fullName ;
	sh:values [
		sh:prefixes <http://example.com/ns> ;
		sh:select """
			SELECT ?fullName
			WHERE {
				$this ex:firstName ?firstName .
				$this ex:lastName ?lastName .
				BIND (CONCAT(?firstName, " ", ?lastName) AS ?fullName) .
			}
		"""
	] ;
	sh:datatype xsd:string .

<http://example.com/ns>
	a owl:Ontology ;
	sh:declare [
		sh:prefix "ex" ;
		sh:namespace "http://example.com/ns#"^^xsd:anyURI ;
	] .
						
```

This example also illustrates the use of `sh:prefixes` to insert PREFIX declarations into the beginning of the query before parsing.
Note that the query is executed with the current focus node pre-bound to the variable `this`.

**Example: Dynamically computed target nodes using a node expression based on a SPARQL query**

Here is an example use of a select expression, computing the target nodes of a shape to consist of all instances of
`ex:Person` where the `ex:age` is less than `18`.

```
ex:ChildShape
	a sh:NodeShape ;
	rdfs:label "Child shape" ;
	rdfs:comment "This shape applies to all persons under 18 years of age." ;
	sh:targetNode [
		sh:select """
			PREFIX ex: <http://example.com/ns#>
			SELECT ?person
			WHERE {
				?person a/rdfs:subClassOf* ex:Person .
				?person ex:age ?age .
				FILTER (?age < 18) .
			}
		"""
	] .
						
```

From the following data graph, only `ex:Benjamin` is a target node.

```
ex:Benjamin
	a ex:Person ;
	ex:age 17 .

ex:Klaus
	a ex:Person ;
	ex:age 48 .

ex:Bernd
	a ex:Person .
						
```

### 6.2 SPARQL Expr Expressions

A node expression that has a value for `sh:sparqlExpr` is called a SPARQL expr expression with the function name
`sh:SPARQLExprExpression`.

A node in an RDF graph
is a well-formed SPARQL expr expression if it is a blank node
that has exactly one value for the predicate `sh:sparqlExpr`
and that value is a literal with datatype `xsd:string`.
A well-formed SPARQL expr expression can have at most one value for the property
`sh:prefixes` and this value is an IRI or a blank node.  
  
Let `$EXPR$` be the value of `sh:sparqlExpr` and `$PREFIXES$`
be the SPARQL prefixes block resulting from the [prefix handling rules](#sparql-prefixes) using the value of `sh:prefixes`;
then `select` is defined as the string where `$EXPR$` and `$PREFIXES$` are inserted as into   
  
`$PREFIXES$ SELECT ($EXPR$ AS ?result) WHERE {}`  
  
`select` is a valid SPARQL 1.2 SELECT query.

The output nodes of an SPARQL expr expression are the list `resultNodes` consisting of exactly the bindings of the (only)
variable that is projected from the `SELECT` clause of the `select` query as defined [above](#syntax-rule-SPARQLExprExpression-template)
when the query is evaluated against the focus graph.
The value of `focusNode` is pre-bound as the value of the SPARQL variable `this`.
The value of each scope variable is pre-bound as a SPARQL variable with the same name and value.
If the name of a variable in scope is not a string literal, use `"arg" + str(name)`.
For example, if the variable name is `"0"^^xsd:integer`, use `arg0`.
A failure is produced when one of the scope variables is called `this`.
  
  
`evalExpr(expr, focusGraph, focusNode, scope) -> resultNodes`

*The remainder of this section is non-normative.*

**Example: A dynamically computed property using a SPARQL expr expression**

Here is an example use of an SPARQL expr expression, computing the values of a property shape for the property
"uri length" as the length of the IRI of the focus node.

```
ex:Resource-uriLength
	a sh:PropertyShape ;
	sh:name "uri length" ;
	sh:path ex:uriLength ;
	sh:values [
		sh:sparqlExpr "STRLEN(STR($this))" ;
	] ;
	sh:datatype xsd:integer .
						
```

When applied to a focus node with URI `http://example.com/ns#Test` the result will be `26`.
This produces the same results as this variation:

```
ex:Resource-uriLength
	a sh:PropertyShape ;
	sh:name "uri length" ;
	sh:path ex:uriLength ;
	sh:values [
		sh:select """
			SELECT (STRLEN(STR($this)) AS ?result)
			WHERE {
			}
		""" ;
	] ;
	sh:datatype xsd:integer .
						
```

Note that the query is executed with the current focus node pre-bound to the variable `this`.

## 7. Declaring SPARQL Functions based on Node Expressions

defines Custom List Parameter Functions
as a mechanism to declare new node expression functions.
These can be evaluated as part of other SHACL node expressions, but may also be useful to other engines
that support function-like execution.

The SPARQL specification defines an extension point that
enables certain SPARQL engines to provide additional SPARQL functions.
This section introduces a declarative mechanism allowing SPARQL processors to make SHACL list parameter functions
available as SPARQL functions using that extension point.

### 7.1 Example SPARQL Function using general Node Expressions

**Example: An example custom function using shnex: node expressions**

This function takes a class as its (only) parameter and returns the number of instances of that class.

```
ex:instanceCount
	a sh:ListParameterExpressionFunction ;
	rdfs:label "instance count"@en ;
	rdfs:subClassOf sh:ListParameterExpression ;
	sh:bodyExpression [
		shnex:count [
			shnex:instancesOf [
				shnex:arg 0
			]
		]
	] ;
	sh:parameter [
		a sh:Parameter ;
		sh:path shnex:arg0 ;
		sh:name "class" ;
		sh:description "The class to count the instances of." ;
		sh:nodeKind sh:IRI ;
	] .
						
```

A SPARQL engine that supports SPARQL functions based on node expressions is able
to process a SPARQL query such as the following:

```
SELECT ?class ?count
WHERE {
	?class a owl:Class .
	BIND (ex:instanceCount(?class) AS ?count) .
}
					
```

### 7.2 Example SPARQL Functions using SPARQL-based Node Expressions

The following custom list parameter functions use "nested" SPARQL queries at evaluation time.

**Example: An example custom function using sh:sparqlExpr**

This function takes two parameters and uses a SPARQL expr expression as its body expression.
In that SPARQL expression, the variables `$arg0` and `$arg1` are used to access the list parameter values.

```
ex:spacedConcat
	a sh:ListParameterExpressionFunction ;
	rdfs:label "spaced concat"@en ;
	rdfs:subClassOf sh:ListParameterExpression ;
	sh:bodyExpression [
		sh:sparqlExpr "CONCAT($arg0, ' ', $arg1)"
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

A SPARQL engine that supports SPARQL functions based on node expressions is able
to process a SPARQL query such as the following:

```
SELECT ?person ?fullName
WHERE {
	?person a ex:Person .
	?person ex:firstName ?firstName .
	?person ex:lastName ?lastName .
	BIND (ex:spacedConcat(?firstName, ?lastName) AS ?fullName) .
}
					
```

The following example uses a `sh:select` node expression as its body.

**Example: An example custom function using sh:select**

This function takes two parameters and uses a SPARQL expr expression as its body expression.
In that SPARQL expression, the variables `$arg0` and `$arg1` are used to access the list parameter values.

```
ex:langLabelCount
    a sh:ListParameterExpressionFunction ;
    rdfs:label "lang label count"@en ;
    rdfs:subClassOf sh:ListParameterExpression ;
    sh:bodyExpression [
		sh:select """
			PREFIX ex: <http://example.com/ns#>
			PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
			SELECT (COUNT(?label) AS ?result)
			WHERE {
				?predicate rdfs:subPropertyOf* rdfs:label .
				$arg0 ?predicate ?label .
				BIND (COALESCE($arg1, 'en') AS ?matchLang) .
				FILTER langMatches(lang(?label), ?matchLang) .
			}
		""" ;
	] ;
	sh:parameter [
		a sh:Parameter ;
		sh:path shnex:arg0 ;
		sh:name "subject" ;
		sh:description "The subject node to get the label count of." ;
		sh:nodeKind sh:IRI ;
	] ;
	sh:parameter [
		a sh:Parameter ;
		sh:path shnex:arg1 ;
		sh:name "match language" ;
		sh:description "The language to filter, defaulting to 'en'." ;
		sh:datatype xsd:string ;
		sh:defaultValue "en" ;
		sh:optional true ;
	] .
						
```

This function accepts an optional parameter for the match language, as declared using the
`sh:optional true` triple.
However, note that the SHACL constraints from the `sh:parameter` declarations are
not automatically enforced, nor will the declared `sh:defaultValue` be used at runtime.
These mainly serve documentation purposes.

```
ex:Cougar
	rdfs:label "Cougar"@en ;
	rdfs:label "Mountain Lion"@en-US ;
	rdfs:label "Puma"@de .

# Example SPARQL function calls:
#   ex:langLabelCount(ex:Cougar, 'en') = 2
#   ex:langLabelCount(ex:Cougar) = 2
#   ex:langLabelCount(ex:Cougar, 'de') = 1
#   ex:langLabelCount(?unbound, 'en') = SPARQL error
						
```

### 7.3 Evaluation of Custom SPARQL Functions

This document does not define exact constraints on how and when such custom SPARQL functions are added.
The recommendation is that SPARQL engines SHOULD register a function for any SHACL instance of
`sh:ListParameterExpressionFunction` from any provided shapes graph.
If a function with the same IRI is already registered, SHACL engines MUST ignore the
attempt to redefine it unless the function was previously added as a custom SPARQL function.
A SPARQL engine MUST NOT modify the registered SPARQL functions while it is executing any SPARQL query.

Let `f` be the `iri` of a SPARQL function call
and `args` be the list of `Expression` arguments.
Let `function` be the corresponding custom list parameter function in the graph
where it has been defined, with `f` as its IRI.

Evaluate each SPARQL expression from `args`, yielding a new list of nodes `nodesList`.
Where the evaluation has caused an error,
the result of the SPARQL function call is also an error,
unless the corresponding `sh:parameter` for the argument has `sh:optional true`.
In that case, the argument will be unbound in the scope.

Let `rs` be the output nodes
of `evalExpr(function, focusGraph, f, scope)` where `focusGraph` is the
currently active query graph from the SPARQL context, and `scope` is the map of evaluated
arguments from `nodesList` with the index of the argument as the variable name (map key).

If the list of output nodes `rs` has exactly one member, then return that node.
Otherwise, or if the evaluation produces an evaluation failure,
the result of the SPARQL function call is an error.

**Note:** During the evaluation of SPARQL queries, there is no dedicated focus node.
Instead, the `focusNode` passed into a custom SPARQL function based on a node expression
is the IRI of the function itself.

## A. Pre-binding of Variables in SPARQL Queries

Some features of SHACL-SPARQL rely on the concept of pre-binding of variables as defined in this section.

This feature is "at risk" and may be changed (not removed)
to align with currently ongoing work in the RDF and SPARQL 1.2 work in this area.
Originally discussed as [Issue 647](https://github.com/w3c/data-shapes/issues/647).

The definition of pre-binding used by SHACL requires the following restrictions on SPARQL queries.
SHACL-SPARQL processors MUST report a failure when it is operating on a shapes graph
that contains SHACL-SPARQL queries (via `sh:ask`, `sh:construct` and `sh:select`)
that are executed with pre-bound variables and violate any of these "MUST" restrictions.
Note that the term *potentially pre-bound variables* includes the variables `this`,
`value` (for ASK queries),
and any variables that represent the parameters of the constraint component that uses the query.

- SPARQL queries MUST not contain a `MINUS` clause
- SPARQL queries MUST not contain a `VALUES` clause that mentions any potentially pre-bound variable
- SPARQL queries MUST not use the syntax form ​​`AS ?var` for any potentially pre-bound variable

Furthermore, SPARQL queries SHOULD not contain a federated query (`SERVICE`).
Implementations that do not permit `SERVICE` MUST report a failure as mentioned above.
However, it is acknowledged that some SPARQL implementations use the `SERVICE` keyword as a syntax for
specific (typically local) operations and therefore the keyword is not generally disallowed.

For solution mapping `μ`, define `Table(μ)` to be the multiset formed from `μ`.

`Table(μ) = { μ }`  
   `Card[μ] = 1`

Define the *Values Insertion* function `Replace(X, μ)` to
replace each occurrence `Y` of a
Basic Graph Pattern,
Property Path Expression,
`Graph(Var, pattern)`
in `X` with `join(Y, Table(μ))`.

The evaluation of the SPARQL Query
`Q = (E, DS, QF)` with *pre-bound* variables `μ`
is defined as the evaluation of SPARQL query `Q' = (Replace(E, μ), DS, QF)`.

## B. Summary of Syntax Rules

This section enumerates all normative syntax rules of this document.
This section is automatically generated from other parts of this spec and hyperlinks are provided back
into the prose if the context of the rule in unclear.
Nodes that violate these rules in a shapes graph are ill-formed.

| Syntax Rule Id | Syntax Rule Text |
| --- | --- |

## C. Potential SPARQL Definitions of SHACL Core Constraint Validators

This appendix uses parts of SPARQL 1.2 in non-normative alternative definitions of the semantics of constraint components and targets
from shacl12-core.
While these may help some implementers, SPARQL is not required for the implementation of the SHACL Core language.

SPARQL variables using the `$` marker represent external bindings that are pre-bound or, in the case of `$PATH`, substituted in the SPARQL query before execution (as explained in [4.3 Validation with SPARQL-based Constraint Components](#constraint-components-validation)).

### C.1 sh:targetClass

The following query expresses a potential definition of class targets in SPARQL.
The variable `targetClass` will be pre-bound to the given value of `sh:targetClass`.
All bindings of the variable `this` from the solutions become focus nodes.

```
SELECT DISTINCT ?this    # ?this is the focus node
WHERE {
	?this rdf:type/rdfs:subClassOf* $targetClass .
}
```

### C.2 sh:targetSubjectsOf

The following query expresses a potential definition of subjects-of targets in SPARQL.
The variable `targetSubjectsOf` will be pre-bound to the given value of `sh:targetSubjectsOf`.
All bindings of the variable `this` from the solutions become focus nodes.

```
SELECT DISTINCT ?this    # ?this is the focus node
WHERE {
	?this $targetSubjectsOf ?any .
}
```

### C.3 sh:targetObjectsOf

The following query expresses a potential definition of objects-of targets in SPARQL.
The variable `targetObjectsOf` will be pre-bound to the given value of `sh:targetObjectsOf`.
All bindings of the variable `this` from the solutions become focus nodes.

```
SELECT DISTINCT ?this    # ?this is the focus node
WHERE {
	?any $targetObjectsOf ?this .
}
```

### C.4 sh:class

The following query expresses a potential SPARQL-based validator for sh:class.

```
ASK {
	$value rdf:type/rdfs:subClassOf* $class .
}
```

### C.5 sh:nodeKind

The following query expresses a potential SPARQL-based validator for sh:nodeKind.

```
ASK {
	FILTER ((isIRI($value) && $nodeKind IN ( sh:IRI, sh:BlankNodeOrIRI, sh:IRIOrLiteral ) ) ||
		(isLiteral($value) && $nodeKind IN ( sh:Literal, sh:BlankNodeOrLiteral, sh:IRIOrLiteral ) ) ||
		(isBlank($value)   && $nodeKind IN ( sh:BlankNode, sh:BlankNodeOrIRI, sh:BlankNodeOrLiteral ) )) .
}
```

### C.6 sh:minExclusive (etc)

The following query expresses a potential SPARQL-based validator for sh:minExclusive.
The SPARQL expression produces an error if the value node cannot be compared to the specified range,
for example when someone compares a string with an integer.
If the comparison cannot be performed, then there is a validation result.
This is different from, say, a plain SPARQL query, in which such errors would silently not lead to any results.

```
ASK {
	FILTER ($minExclusive < $value)
}
```

Similar definitions are possible for:

- sh:minInclusive: <=
- sh:maxExclusive: >
- sh:maxInclusive: >=

### C.7 sh:minLength

The following query expresses a potential SPARQL-based validator for sh:minLength.

```
ASK {
	FILTER (STRLEN(str($value)) >= $minLength) .
}
```

### C.8 sh:maxLength

The following query expresses a potential SPARQL-based validator for sh:maxLength.

```
ASK {
	FILTER (STRLEN(str($value)) <= $maxLength) .
}
```

### C.9 sh:pattern

The following query expresses a potential SPARQL-based validator for sh:pattern.

```
ASK {
	FILTER (!isBlank($value) && IF(bound($flags), regex(str($value), $pattern, $flags), regex(str($value), $pattern)))
}
```

### C.10 sh:disjoint

The following query expresses a potential SPARQL-based validator for sh:disjoint.

```
SELECT DISTINCT $this ?value
WHERE {
	$this $PATH ?value .
	$this $disjoint ?value .
}
```

### C.11 sh:lessThan

The following query expresses a potential SPARQL-based validator for sh:lessThan.

```
SELECT $this ?value
WHERE {
	$this $PATH ?value .
	$this $lessThan ?otherValue .
	BIND (?value < ?otherValue AS ?result) .
	FILTER (!bound(?result) || !(?result)) .
}
```

### C.12 sh:lessThanOrEquals

The following query expresses a potential SPARQL-based validator for sh:lessThanOrEquals.

```
SELECT $this ?value
WHERE {
	$this $PATH ?value .
	$this $lessThanOrEquals ?otherValue .
	BIND (?value <= ?otherValue AS ?result) .
	FILTER (!bound(?result) || !(?result)) .
}
```

## D. Security and Privacy Considerations

Note that SPARQL key words such as `GRAPH` and `FROM` may provide access to
graphs other than the active data graph in the dataset.
A SHACL-SPARQL engine should ensure that the SPARQL engine does not provide access to
named graphs which the user who has triggered the validation is not permitted to access.

Security considerations of SHACL-SPARQL include all the
security considerations of
SPARQL,
SPARQL Federated Query (`SERVICE`) and
SHACL Core.

## E. Acknowledgements

Original SHACL core specifications were produced by the RDF Data Shapes Working Group.
See the [Core specification's Acknowledgements section](https://www.w3.org/TR/2017/REC-shacl-20170720/#ack) and
the [Advanced Features specification's Acknowledgements section](https://www.w3.org/TR/2017/NOTE-shacl-af-20170608/#ack).

## F. Changes between the original SHACL specifications and SHACL 1.2 SPARQL

- Added the node expression function [`sh:SelectExpression`](#SelectExpression), see [Issue 288](https://github.com/w3c/data-shapes/issues/288)
- Added support for annotation properties, see [Issue 327](https://github.com/w3c/data-shapes/issues/327)
- Added the node expression function [`sh:SPARQLExprExpression`](#SPARQLExprExpression), see [Issue 315](https://github.com/w3c/data-shapes/issues/315)
- Clarified that VALUES clauses are only disallowed when they mention [pre-bound variables](#pre-binding) and removed the restriction on sub-SELECTs, see [Issue 159](https://github.com/w3c/data-shapes/issues/159)
- SERVICE clauses are conditionally permitted, see [Issue 374](https://github.com/w3c/data-shapes/issues/374)
- Removed support for the optional pre-bound variables `shapesGraph` and `currentShape`, see [Issue 426](https://github.com/w3c/data-shapes/issues/426)
- SPARQL constraints can now directly specify a `sh:severity`, see [Issue 573](https://github.com/w3c/data-shapes/issues/573)
- If no `sh:prefixes` are present, the system will use any `sh:prefix`/`sh:namespace` pair declared in any `sh:ShapesGraph`, see [Issue 176](https://github.com/w3c/data-shapes/issues/176)
