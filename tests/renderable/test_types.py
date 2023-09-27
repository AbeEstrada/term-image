from typing import Any

import pytest

from term_image.geometry import Size
from term_image.renderable import (
    Frame,
    IncompatibleArgsNamespaceError,
    IncompatibleRenderArgsError,
    NoArgsNamespaceError,
    NoDataNamespaceError,
    Renderable,
    RenderArgs,
    RenderArgsDataError,
    RenderArgsError,
    RenderData,
    UninitializedDataFieldError,
    UnknownArgsFieldError,
    UnknownDataFieldError,
)
from term_image.renderable._types import RenderArgsData

# Renderables ==================================================================


class Foo(Renderable):
    @classmethod
    def _finalize_render_data_(cls, render_data):
        render_data[__class__].bar = render_data[__class__].foo
        super()._finalize_render_data_(render_data)

    class Args(RenderArgs.Namespace):
        foo: Any = "FOO"
        bar: Any = "BAR"

    class _Data_(RenderData.Namespace):
        foo: Any
        bar: Any


# Utils ========================================================================


class NamespaceBase(RenderArgsData.Namespace, _base=True):
    def __init__(self, fields=None):
        super().__init__(fields or {})


# Tests ========================================================================


class TestFrame:
    args = (0, 1, Size(1, 1), " ")

    class TestFields:
        args = (0, 1, Size(1, 1), " ")

        @pytest.mark.parametrize("number", [0, 10])
        def test_number(self, number):
            frame = Frame(number, *self.args[1:])
            assert frame.number is number

        @pytest.mark.parametrize("duration", [1, 100])
        def test_duration(self, duration):
            frame = Frame(*self.args[:1], duration, *self.args[2:])
            assert frame.duration is duration

        @pytest.mark.parametrize("size", [Size(1, 3), Size(100, 30)])
        def test_size(self, size):
            frame = Frame(*self.args[:2], size, *self.args[3:])
            assert frame.render_size is size

        @pytest.mark.parametrize("render", [" ", " " * 10])
        def test_render(self, render):
            frame = Frame(*self.args[:3], render)
            assert frame.render_output is render

    @pytest.mark.parametrize("render", [" ", " " * 10])
    def test_str(self, render):
        frame = Frame(*self.args[:3], render)
        assert str(frame) is render

    @pytest.mark.parametrize("field", Frame._fields)
    def test_immutability(self, field):
        frame = Frame(*self.args)
        with pytest.raises(AttributeError):
            setattr(frame, field, Ellipsis)

        with pytest.raises(AttributeError):
            delattr(frame, field)

    @pytest.mark.parametrize("args", [args, (9, 100, Size(10, 10), " " * 10)])
    def test_equality(self, args):
        assert Frame(*args) == Frame(*args)

    @pytest.mark.parametrize(
        "args1, args2",
        [
            (args, (9, 100, Size(10, 10), " " * 10)),
            (args, (99, 1000, Size(100, 100), " " * 100)),
        ],
    )
    def test_unequality(self, args1, args2):
        assert Frame(*args1) != Frame(*args2)


class TestNamespaceMeta:
    def test_multiple_namespace_bases(self):
        class A(NamespaceBase):
            a: None

        class B(NamespaceBase):
            b: None

        with pytest.raises(RenderArgsDataError, match="Multiple .* baseclasses"):

            class C(A, B):
                pass

    class TestFields:
        def test_no_field(self):
            with pytest.raises(RenderArgsDataError, match="No field"):

                class Namespace(NamespaceBase):
                    pass

        def test_define(self):
            class Namespace(NamespaceBase):
                foo: None
                bar: None

            assert Namespace.__dict__["__slots__"] == ("foo", "bar")
            assert Namespace._FIELDS == {"foo": None, "bar": None}

        def test_inherit(self):
            class A(NamespaceBase):
                a: None
                b: None

            class B(A):
                pass

            assert B.__dict__["__slots__"] == ()
            assert B._FIELDS == {"a": None, "b": None}

        def test_inherit_and_define(self):
            class A(NamespaceBase):
                a: None
                b: None

            with pytest.raises(RenderArgsDataError, match="inherit and define"):

                class B(A):
                    c: None
                    d: None

        def test_inherit_false(self):
            class A(NamespaceBase):
                a: None
                b: None

            class B(A, inherit=False):
                c: None
                d: None

            assert B.__dict__["__slots__"] == ("c", "d")
            assert B._FIELDS == {"c": None, "d": None}

            with pytest.raises(RenderArgsDataError, match="No field"):

                class B(A, inherit=False):
                    pass

    class TestRenderCls:
        def test_association(self):
            class Namespace(NamespaceBase):
                foo: None

            assert Namespace.get_render_cls() is None

            Namespace._RENDER_CLS = Renderable
            assert Namespace.get_render_cls() is Renderable

        class TestInheritTrue:
            def test_subclass_before_association(self):
                class A(NamespaceBase):
                    a: None

                class B(A):
                    pass

                assert B.get_render_cls() is None

                A._RENDER_CLS = Renderable
                assert B.get_render_cls() is Renderable

            def test_subclass_after_association(self):
                class A(NamespaceBase):
                    a: None

                A._RENDER_CLS = Renderable

                class B(A):
                    pass

                assert B.get_render_cls() is Renderable

        class TestInheritFalse:
            def test_subclass_before_association(self):
                class A(NamespaceBase):
                    a: None

                class B(A, inherit=False):
                    b: None

                assert B.get_render_cls() is None

                A._RENDER_CLS = Renderable
                assert B.get_render_cls() is None

            def test_subclass_after_association(self):
                class A(NamespaceBase):
                    a: None

                A._RENDER_CLS = Renderable

                class B(A, inherit=False):
                    b: None

                assert B.get_render_cls() is None

    class TestRequiredConstructorParameters:
        def test_new(self):
            with pytest.raises(TypeError, match="__new__.* required parameter"):

                class Namespace(NamespaceBase):  # noqa: F811
                    foo: None

                    def __new__(self, foo):
                        pass

        def test_init(self):
            with pytest.raises(TypeError, match="__init__.* required parameter"):

                class Namespace(NamespaceBase):
                    foo: None

                    def __init__(self, foo):
                        pass


class TestNamespace:
    class Namespace(NamespaceBase):
        _RENDER_CLS = Renderable
        foo: int
        bar: int

    def test_cannot_instantiate_unassociated(self):
        class Namespace(NamespaceBase):
            foo: None

        with pytest.raises(TypeError, match="Cannot instantiate"):
            Namespace()

    def test_delattr(self):
        namespace = self.Namespace(dict(foo=1, bar=2))
        with pytest.raises(AttributeError, match="Cannot delete"):
            del namespace.foo
        with pytest.raises(AttributeError, match="Cannot delete"):
            del namespace.bar

    def test_get_render_cls(self):
        class Namespace(NamespaceBase):
            foo: None

        assert Namespace.get_render_cls() is None

        Namespace._RENDER_CLS = Renderable
        assert Namespace.get_render_cls() is Renderable

        namespace = Namespace(dict(foo=None))
        assert namespace.get_render_cls() is Renderable


class TestRenderArgs:
    def test_args(self):
        with pytest.raises(TypeError, match="'render_cls'"):
            RenderArgs(Ellipsis)

        with pytest.raises(TypeError, match="second argument"):
            RenderArgs(Renderable, Ellipsis)

        with pytest.raises(TypeError, match=r"'namespaces\[0\]'"):
            RenderArgs(Renderable, RenderArgs(Renderable), Ellipsis)

        with pytest.raises(TypeError, match=r"'namespaces\[1\]'"):
            RenderArgs(Foo, Foo.Args(), Ellipsis)

    def test_base(self):
        render_args = RenderArgs(Renderable)
        assert render_args.render_cls is Renderable
        assert set(render_args) == set()

        with pytest.raises(NoArgsNamespaceError):
            render_args[Renderable]

    def test_render_cls(self):
        render_args = RenderArgs(Foo)
        assert render_args.render_cls is Foo

    class TestNamespaces:
        class TestCompatibility:
            class A(Renderable):
                class Args(RenderArgs.Namespace):
                    foo: None = None

            class B(A):
                class Args(RenderArgs.Namespace):
                    foo: None = None

            class C(A):
                class Args(RenderArgs.Namespace):
                    foo: None = None

            @pytest.mark.parametrize(
                "cls1, cls2", [(A, A), (B, A), (B, B), (C, A), (C, C)]
            )
            def test_compatible(self, cls1, cls2):
                assert RenderArgs(cls1, cls2.Args()) == RenderArgs(cls1)

            @pytest.mark.parametrize("cls1, cls2", [(A, B), (A, C), (B, C), (C, B)])
            def test_incompatible(self, cls1, cls2):
                with pytest.raises(IncompatibleArgsNamespaceError):
                    RenderArgs(cls1, cls2.Args())

        def test_default(self):
            render_args = RenderArgs(Foo)
            assert render_args[Foo] == Foo.Args()

        def test_non_default(self):
            namespace = Foo.Args("bar", "foo")
            render_args = RenderArgs(Foo, namespace)
            assert render_args[Foo] is namespace

        def test_multiple_with_same_render_cls(self):
            namespace_foo = Foo.Args(foo="bar")
            namespace_bar = Foo.Args(bar="foo")

            render_args = RenderArgs(Foo, namespace_foo, namespace_bar)
            assert render_args[Foo] is namespace_bar

            render_args = RenderArgs(Foo, namespace_bar, namespace_foo)
            assert render_args[Foo] is namespace_foo

    class TestInitRenderArgs:
        class TestCompatibility:
            class A(Renderable):
                pass

            class B(A):
                pass

            class C(A):
                pass

            @pytest.mark.parametrize(
                "cls1, cls2",
                [
                    (A, Renderable),
                    (A, A),
                    (B, Renderable),
                    (B, A),
                    (B, B),
                    (C, Renderable),
                    (C, A),
                    (C, C),
                ],
            )
            def test_compatible(self, cls1, cls2):
                assert RenderArgs(cls1, RenderArgs(cls2)) == RenderArgs(cls1)

            @pytest.mark.parametrize(
                "cls1, cls2",
                [
                    (Renderable, A),
                    (Renderable, B),
                    (Renderable, C),
                    (A, B),
                    (A, C),
                    (B, C),
                    (C, B),
                ],
            )
            def test_incompatible(self, cls1, cls2):
                init_render_args = RenderArgs(cls2)
                with pytest.raises(IncompatibleRenderArgsError):
                    RenderArgs(cls1, init_render_args)

        def test_default(self):
            render_args = RenderArgs(Foo)
            assert render_args[Foo] == Foo.Args()
            assert render_args == RenderArgs(Foo, None)

        def test_non_default(self):
            init_render_args = RenderArgs(Foo, Foo.Args("bar", "foo"))
            render_args = RenderArgs(Foo, init_render_args)
            assert render_args == init_render_args
            assert render_args[Foo] == Foo.Args("bar", "foo")
            assert render_args[Foo] is init_render_args[Foo]

    def test_eq(self):
        class Bar(Renderable):
            class Args(RenderArgs.Namespace):
                bar: str = "BAR"

        class Baz(Bar):
            class Args(RenderArgs.Namespace):
                baz: str = "BAZ"

        bar_args = RenderArgs(Bar)
        assert bar_args == RenderArgs(Bar)
        assert bar_args == RenderArgs(Bar, Bar.Args())

        bar_args_bar = RenderArgs(Bar, Bar.Args("bar"))
        assert bar_args_bar == RenderArgs(Bar, Bar.Args("bar"))
        assert bar_args_bar != bar_args

        baz_args = RenderArgs(Baz)
        assert baz_args == RenderArgs(Baz)
        assert baz_args == RenderArgs(Baz, Bar.Args())
        assert baz_args == RenderArgs(Baz, Baz.Args())
        assert baz_args == RenderArgs(Baz, Bar.Args(), Baz.Args())
        assert baz_args == RenderArgs(Baz, Baz.Args(), Bar.Args())
        assert baz_args != bar_args
        assert baz_args != bar_args_bar

        baz_args_bar = RenderArgs(Baz, Bar.Args("bar"))
        assert baz_args_bar == RenderArgs(Baz, Bar.Args("bar"))
        assert baz_args_bar == RenderArgs(Baz, Bar.Args("bar"), Baz.Args())
        assert baz_args_bar == RenderArgs(Baz, Baz.Args(), Bar.Args("bar"))
        assert baz_args_bar != bar_args
        assert baz_args_bar != bar_args_bar
        assert baz_args_bar != baz_args

        baz_args_baz = RenderArgs(Baz, Baz.Args("baz"))
        assert baz_args_baz == RenderArgs(Baz, Baz.Args("baz"))
        assert baz_args_baz == RenderArgs(Baz, Bar.Args(), Baz.Args("baz"))
        assert baz_args_baz == RenderArgs(Baz, Baz.Args("baz"), Bar.Args())
        assert baz_args_baz != bar_args
        assert baz_args_baz != bar_args_bar
        assert baz_args_baz != baz_args
        assert baz_args_baz != baz_args_bar

        baz_args_bar_baz = RenderArgs(Baz, Bar.Args("bar"), Baz.Args("baz"))
        assert baz_args_bar_baz == RenderArgs(Baz, Bar.Args("bar"), Baz.Args("baz"))
        assert baz_args_bar_baz == RenderArgs(Baz, Baz.Args("baz"), Bar.Args("bar"))
        assert baz_args_bar_baz != bar_args
        assert baz_args_bar_baz != bar_args_bar
        assert baz_args_bar_baz != baz_args
        assert baz_args_bar_baz != baz_args_bar
        assert baz_args_bar_baz != baz_args_baz

    def test_getitem(self):
        class Bar(Foo):
            pass

        class Baz(Bar):
            pass

        render_args = RenderArgs(Bar)

        with pytest.raises(TypeError, match="'render_cls'"):
            render_args[Ellipsis]

        with pytest.raises(TypeError, match="'render_cls'"):
            render_args[[]]

        with pytest.raises(NoArgsNamespaceError):
            render_args[Bar]

        with pytest.raises(ValueError, match="'Bar' is not a subclass of 'Baz'"):
            render_args[Baz]

        assert isinstance(render_args[Foo], Foo.Args)

    def test_hash(self):
        foo_args_default = RenderArgs(Foo)
        assert hash(foo_args_default) == hash(RenderArgs(Foo))

        foo_args_foo_bar = RenderArgs(Foo, Foo.Args(foo="bar", bar="foo"))
        assert hash(foo_args_foo_bar) == hash(
            RenderArgs(Foo, Foo.Args(foo="bar", bar="foo"))
        )

        foo_args = RenderArgs(Foo, Foo.Args(foo=[]))
        with pytest.raises(TypeError):
            hash(foo_args)

    def test_iter(self):
        class A(Renderable):
            class Args(RenderArgs.Namespace):
                foo: None = None

        class B(A):
            class Args(RenderArgs.Namespace):
                foo: None = None

        class C(B):
            class Args(RenderArgs.Namespace):
                foo: None = None

        assert {*RenderArgs(A)} == {A.Args()}
        assert {*RenderArgs(B)} == {A.Args(), B.Args()}
        assert {*RenderArgs(C)} == {A.Args(), B.Args(), C.Args()}

    class TestConvert:
        class A(Renderable):
            class Args(RenderArgs.Namespace):
                a: str = "a"

        class B(Renderable):
            class Args(RenderArgs.Namespace):
                b: str = "b"

        class C(A, B):
            class Args(RenderArgs.Namespace):
                c: str = "c"

        class D(C):
            class Args(RenderArgs.Namespace):
                d: str = "d"

        args = (A.Args("1"), B.Args("2"), C.Args("3"), D.Args("4"))

        def test_args(self):
            render_args = RenderArgs(Foo)
            with pytest.raises(TypeError, match="'render_cls'"):
                render_args.convert(Ellipsis)

        def test_same_render_cls(self):
            render_args = RenderArgs(Foo, Foo.Args("bar", "foo"))
            assert render_args.convert(Foo) is render_args

        def test_child(self):
            render_args_a = RenderArgs(self.A, self.args[0])
            render_args_b = RenderArgs(self.B, self.args[1])
            render_args_c = RenderArgs(self.C, *self.args[:3])

            assert render_args_a.convert(self.D) == RenderArgs(self.D, self.args[0])
            assert render_args_b.convert(self.D) == RenderArgs(self.D, self.args[1])
            assert render_args_c.convert(self.D) == RenderArgs(self.D, *self.args[:3])

        def test_parent(self):
            render_args = RenderArgs(self.D, *self.args)
            assert render_args.convert(self.A) == RenderArgs(self.A, self.args[0])
            assert render_args.convert(self.B) == RenderArgs(self.B, self.args[1])
            assert render_args.convert(self.C) == RenderArgs(self.C, *self.args[:3])

        def test_non_parent_child(self):
            render_args = RenderArgs(self.A)
            with pytest.raises(ValueError, match="'B' is not a parent or child of 'A'"):
                render_args.convert(self.B)

            render_args = RenderArgs(self.B)
            with pytest.raises(ValueError, match="'A' is not a parent or child of 'B'"):
                render_args.convert(self.A)

    class TestUpdate:
        def test_args(self):
            class Bar(Renderable):
                pass

            class Baz(Bar):
                pass

            render_args = RenderArgs(Foo)

            with pytest.raises(TypeError, match="first argument"):
                render_args.update(Ellipsis)

            with pytest.raises(TypeError, match="positional argument"):
                render_args.update(Foo, Ellipsis)

            with pytest.raises(TypeError, match="keyword argument"):
                render_args.update(Foo.Args(), foo=Ellipsis)

            # propagated

            with pytest.raises(TypeError, match=r"'namespaces\[1\]'"):
                render_args.update(Foo.Args(), Ellipsis)

            with pytest.raises(ValueError, match="not a subclass"):
                render_args.update(Bar)

            with pytest.raises(NoArgsNamespaceError):
                RenderArgs(Baz).update(Bar)

            with pytest.raises(UnknownArgsFieldError, match="'x'"):
                render_args.update(Foo, x=Ellipsis)

        def test_namespaces(self):
            render_args = RenderArgs(Foo)
            namespace = Foo.Args(foo="bar", bar="foo")
            assert render_args.update(namespace) == RenderArgs(Foo, namespace)
            assert render_args.update(namespace)[Foo] is namespace

            render_args = +Foo.Args(foo="bar")
            namespace = Foo.Args(bar="foo")
            assert render_args.update(Foo.Args()) == RenderArgs(Foo)
            assert render_args.update(namespace) == RenderArgs(Foo, namespace)
            assert render_args.update(namespace)[Foo] is namespace

            render_args = +Foo.Args(bar="foo")
            namespace = Foo.Args(foo="bar")
            assert render_args.update(Foo.Args()) == RenderArgs(Foo)
            assert render_args.update(namespace) == RenderArgs(Foo, namespace)
            assert render_args.update(namespace)[Foo] is namespace

        def test_multiple_namespaces_with_same_render_cls(self):
            args_foo = Foo.Args(foo="bar")
            args_bar = Foo.Args(bar="foo")
            render_args = RenderArgs(Foo)

            assert render_args.update(args_foo, args_bar)[Foo] is args_bar
            assert render_args.update(args_bar, args_foo)[Foo] is args_foo

        def test_fields(self):
            render_args = +Foo.Args(foo="bar")
            assert render_args.update(Foo) == render_args
            assert render_args.update(Foo, foo="bar") == render_args
            assert render_args.update(Foo, foo="foo") == +Foo.Args(foo="foo")
            assert render_args.update(Foo, bar="foo") == +Foo.Args(foo="bar", bar="foo")

    def test_immutability(self):
        render_args = RenderArgs(Foo)
        with pytest.raises(TypeError):
            render_args[Foo] = Foo.Args()

    def test_namespace_source_precedence(self):
        class A(Renderable):
            class Args(RenderArgs.Namespace):
                a: int = 1

        class B(A):
            class Args(RenderArgs.Namespace):
                b: int = 2

        class C(B):
            class Args(RenderArgs.Namespace):
                c: int = 3

        init_render_args = RenderArgs(B, A.Args(10), B.Args(20))
        namespace = A.Args(100)
        render_args = RenderArgs(C, init_render_args, namespace)

        assert render_args[A] is namespace
        assert render_args[B] is init_render_args[B]
        assert render_args[C] is RenderArgs(C)[C]  # default

    class TestOptimizations:
        class TestDefaultsInterned:
            class Bar(Foo):
                pass

            def test_true_positives(self):
                assert RenderArgs(Renderable) is RenderArgs(Renderable)
                assert RenderArgs(Foo) is RenderArgs(Foo)

                render_args = RenderArgs(self.Bar)

                assert render_args is RenderArgs(self.Bar)
                assert render_args is RenderArgs(self.Bar, RenderArgs(Renderable))
                assert render_args is RenderArgs(self.Bar, RenderArgs(Foo))
                assert render_args is RenderArgs(self.Bar, render_args)

            def test_likely_false_positives(self):
                class Baz(Foo):
                    pass

                with pytest.raises(IncompatibleRenderArgsError):
                    RenderArgs(self.Bar, RenderArgs(Baz))

            def test_subclass(self):
                class SubRenderArgs(RenderArgs):
                    pass

                render_args = SubRenderArgs(Renderable)
                assert isinstance(render_args, SubRenderArgs)
                assert render_args is SubRenderArgs(Renderable)

                render_args = SubRenderArgs(Foo)
                assert isinstance(render_args, SubRenderArgs)
                assert render_args is SubRenderArgs(Foo)

        def test_init_render_args_with_same_render_cls_and_without_namespaces(self):
            class Bar(Foo):
                pass

            namespace = Foo.Args(foo="bar", bar="foo")

            foo_render_args = RenderArgs(Foo, namespace)
            assert RenderArgs(Foo, foo_render_args) is foo_render_args

            bar_render_args = RenderArgs(Bar, namespace)
            assert RenderArgs(Bar, bar_render_args) is bar_render_args

        # Actually interned by `RenderableMeta`; testing that they're being used
        def test_default_namespaces_interned(self):
            class A(Renderable):
                class Args(RenderArgs.Namespace):
                    a: None = None

            class B(A):
                class Args(RenderArgs.Namespace):
                    b: None = None

            class C(B):
                class Args(RenderArgs.Namespace):
                    c: None = None

            assert RenderArgs(A)[A] is RenderArgs(B)[A]
            assert RenderArgs(A)[A] is RenderArgs(C)[A]
            assert RenderArgs(B)[B] is RenderArgs(C)[B]


class TestArgsNamespaceMeta:
    class TestFields:
        def test_no_default(self):
            with pytest.raises(RenderArgsError, match="'bar' .* no default"):

                class Namespace(RenderArgs.Namespace):
                    foo: None = None
                    bar: None
                    baz: None = None

        def test_defaults(self):
            class Namespace(RenderArgs.Namespace):
                foo: str = "FOO"
                bar: str = "BAR"

            Namespace.get_fields() == dict(foo="FOO", bar="BAR")


class TestArgsNamespace:
    class Bar(Renderable):
        class Args(RenderArgs.Namespace):
            foo: str = "FOO"
            bar: str = "BAR"

    Namespace = Bar.Args

    class TestConstructor:
        class Bar(Renderable):
            class Args(RenderArgs.Namespace):
                foo: str = "FOO"
                bar: str = "BAR"
                baz: str = "BAZ"

        Namespace = Bar.Args

        def test_args(self):
            with pytest.raises(TypeError, match="'Bar' defines 3 .* 4 .* given"):
                self.Namespace("", "", "", "")

            with pytest.raises(UnknownArgsFieldError, match="'dude'"):
                self.Namespace(dude="dude")

            with pytest.raises(TypeError, match=r"Got multiple .* \('foo',\)"):
                self.Namespace("foo", foo="foo")

        def test_default(self):
            namespace = self.Namespace()
            assert namespace.as_dict() == dict(foo="FOO", bar="BAR", baz="BAZ")

        def test_render_args(self):
            namespace = self.Namespace("foo")
            assert namespace.as_dict() == dict(foo="foo", bar="BAR", baz="BAZ")

            namespace = self.Namespace("foo", "bar")
            assert namespace.as_dict() == dict(foo="foo", bar="bar", baz="BAZ")

            namespace = self.Namespace("foo", "bar", "baz")
            assert namespace.as_dict() == dict(foo="foo", bar="bar", baz="baz")

        def test_render_kwargs(self):
            namespace = self.Namespace(foo="foo")
            assert namespace.as_dict() == dict(foo="foo", bar="BAR", baz="BAZ")

            namespace = self.Namespace(bar="bar")
            assert namespace.as_dict() == dict(foo="FOO", bar="bar", baz="BAZ")

            namespace = self.Namespace(baz="baz")
            assert namespace.as_dict() == dict(foo="FOO", bar="BAR", baz="baz")

            namespace = self.Namespace(foo="foo", bar="bar")
            assert namespace.as_dict() == dict(foo="foo", bar="bar", baz="BAZ")

            namespace = self.Namespace(foo="foo", baz="baz")
            assert namespace.as_dict() == dict(foo="foo", bar="BAR", baz="baz")

            namespace = self.Namespace(bar="bar", baz="baz")
            assert namespace.as_dict() == dict(foo="FOO", bar="bar", baz="baz")

            namespace = self.Namespace(foo="foo", bar="bar", baz="baz")
            assert namespace.as_dict() == dict(foo="foo", bar="bar", baz="baz")

            # Out of order
            namespace = self.Namespace(bar="bar", baz="baz", foo="foo")
            assert namespace.as_dict() == dict(foo="foo", bar="bar", baz="baz")

        def test_render_args_kwargs(self):
            namespace = self.Namespace("foo", bar="bar")
            assert namespace.as_dict() == dict(foo="foo", bar="bar", baz="BAZ")

            namespace = self.Namespace("foo", baz="baz")
            assert namespace.as_dict() == dict(foo="foo", bar="BAR", baz="baz")

            namespace = self.Namespace("foo", bar="bar", baz="baz")
            assert namespace.as_dict() == dict(foo="foo", bar="bar", baz="baz")

            namespace = self.Namespace("foo", "bar", baz="baz")
            assert namespace.as_dict() == dict(foo="foo", bar="bar", baz="baz")

    def test_getattr(self):
        namespace = self.Namespace()
        assert namespace.foo == "FOO"
        assert namespace.bar == "BAR"
        with pytest.raises(UnknownArgsFieldError, match="'baz' for 'Bar'"):
            namespace.baz

    def test_setattr(self):
        namespace = self.Namespace()
        with pytest.raises(AttributeError):
            namespace.foo = "bar"
        with pytest.raises(AttributeError):
            namespace.bar = "foo"

    def test_eq(self):
        namespace_default = self.Namespace()
        assert namespace_default == self.Namespace()
        assert namespace_default == self.Namespace("FOO", "BAR")

        namespace_foo = self.Namespace(foo="foo")
        assert namespace_foo == self.Namespace("foo", "BAR")
        assert namespace_foo == self.Namespace(foo="foo")
        assert namespace_foo != namespace_default

        namespace_bar = self.Namespace(bar="bar")
        assert namespace_bar == self.Namespace("FOO", "bar")
        assert namespace_bar == self.Namespace(bar="bar")
        assert namespace_bar != namespace_default
        assert namespace_bar != namespace_foo

        namespace_foo_bar = self.Namespace("foo", "bar")
        assert namespace_foo_bar == self.Namespace("foo", "bar")
        assert namespace_foo_bar == self.Namespace(foo="foo", bar="bar")
        assert namespace_foo_bar != namespace_default
        assert namespace_foo_bar != namespace_foo
        assert namespace_foo_bar != namespace_bar

    def test_hash(self):
        namespace_default = self.Namespace()
        assert hash(namespace_default) == hash(self.Namespace())

        namespace_foo_bar = self.Namespace("foo", "bar")
        assert hash(namespace_foo_bar) == hash(self.Namespace("foo", "bar"))

        namespace = self.Namespace([])
        with pytest.raises(TypeError):
            hash(namespace)

    class TestOr:
        class A(Renderable):
            class Args(RenderArgs.Namespace):
                a: int = 0

        class B(A):
            class Args(RenderArgs.Namespace):
                b: int = 0

        class C(A):
            class Args(RenderArgs.Namespace):
                c: int = 0

        def test_invalid_type(self):
            A = TestArgsNamespace.TestOr.A
            a = A.Args()

            with pytest.raises(TypeError):
                a | Ellipsis

        class TestNamespace:
            def test_same_render_cls(self):
                A = TestArgsNamespace.TestOr.A
                a1, a2 = A.Args(1), A.Args(2)

                assert a2 | a1 == RenderArgs(A, a1)
                assert a1 | a2 == RenderArgs(A, a2)

            # Render class of *other* is a child of that of *self*
            def test_compatible_child_render_cls(self):
                A = TestArgsNamespace.TestOr.A
                B = TestArgsNamespace.TestOr.B
                C = TestArgsNamespace.TestOr.C
                a, b, c = A.Args(1), B.Args(2), C.Args(3)

                assert a | b == RenderArgs(B, a, b)
                assert a | c == RenderArgs(C, a, c)

            # Render class of *other* is a parent of that of *self*
            def test_compatible_parent_render_cls(self):
                A = TestArgsNamespace.TestOr.A
                B = TestArgsNamespace.TestOr.B
                C = TestArgsNamespace.TestOr.C
                a, b, c = A.Args(1), B.Args(2), C.Args(3)

                assert b | a == RenderArgs(B, a, b)
                assert c | a == RenderArgs(C, a, c)

            def test_incompatible_render_cls(self):
                B = TestArgsNamespace.TestOr.B
                C = TestArgsNamespace.TestOr.C
                b, c = B.Args(2), C.Args(3)

                with pytest.raises(IncompatibleArgsNamespaceError):
                    b | c

                with pytest.raises(IncompatibleArgsNamespaceError):
                    c | b

        class TestRenderArgs:
            # Render class of *other* is a child of that of *self*
            def test_compatible_child_render_cls(self):
                A = TestArgsNamespace.TestOr.A
                B = TestArgsNamespace.TestOr.B
                C = TestArgsNamespace.TestOr.C
                a, b, c = A.Args(1), B.Args(2), C.Args(3)

                assert a | RenderArgs(B, b) == RenderArgs(B, a, b)
                assert a | RenderArgs(C, c) == RenderArgs(C, a, c)

            # Render class of *other* is a parent of that of *self*
            def test_compatible_parent_render_cls(self):
                A = TestArgsNamespace.TestOr.A
                B = TestArgsNamespace.TestOr.B
                C = TestArgsNamespace.TestOr.C
                a, b, c = A.Args(1), B.Args(2), C.Args(3)

                assert b | RenderArgs(A, a) == RenderArgs(B, a, b)
                assert c | RenderArgs(A, a) == RenderArgs(C, a, c)

            def test_incompatible_render_cls(self):
                B = TestArgsNamespace.TestOr.B
                C = TestArgsNamespace.TestOr.C
                b, c = B.Args(2), C.Args(3)

                with pytest.raises(IncompatibleRenderArgsError):
                    b | RenderArgs(C)

                with pytest.raises(IncompatibleRenderArgsError):
                    c | RenderArgs(B)

    def test_pos(self):
        assert +self.Namespace() == RenderArgs(self.Bar)
        assert +self.Namespace("bar", "foo") == RenderArgs(
            self.Bar, self.Namespace("bar", "foo")
        )

    class TestRor:
        """The reflected operation is invoked if either:

        * type(RHS) is a subclass of type(LHS) and provides a different implementation
          of the reflected operation, or
        * type(LHS) does not implement the [non-reflected] operation against type(RHS)
          i.e `LHS.__non_reflected__(RHS)` returns `NotImplemented`.
        """

        def test_invalid_type(self):
            class A(Renderable):
                class Args(RenderArgs.Namespace):
                    a: int = 0

            a = A.Args()
            with pytest.raises(TypeError):
                Ellipsis | a

        class TestNamespace:
            def test_same_render_cls(self):
                class A(Renderable):
                    class Args(RenderArgs.Namespace):
                        a: int = 0

                    class SubArgs(Args):
                        def __ror__(self, other):  # See docstring of `TestRor`
                            return super().__ror__(other)

                a, a_sub = A.Args(1), A.SubArgs(2)
                assert a | a_sub == RenderArgs(A, a_sub)

            # Render class of *other* is a child of that of *self*
            def test_compatible_child_render_cls(self):
                class ArgsC(RenderArgs.Namespace):
                    c: int = 0

                class ArgsB(ArgsC, inherit=False):
                    b: int = 0

                class ArgsA(ArgsC, inherit=False):
                    a: int = 0

                    def __ror__(self, other):  # See docstring of `TestRor`
                        return super().__ror__(other)

                class A(Renderable):
                    Args = ArgsA

                class B(A):
                    Args = ArgsB

                class C(A):
                    Args = ArgsC

                a, b, c = A.Args(1), B.Args(2), C.Args(3)
                assert b | a == RenderArgs(B, a, b)
                assert c | a == RenderArgs(C, a, c)

            # Render class of *other* is a parent of that of *self*
            def test_compatible_parent_render_cls(self):
                class A(Renderable):
                    class Args(RenderArgs.Namespace):
                        a: int = 0

                class B(A):
                    class Args(A.Args, inherit=False):
                        b: int = 0

                        def __ror__(self, other):  # See docstring of `TestRor`
                            return super().__ror__(other)

                class C(A):
                    class Args(A.Args, inherit=False):
                        c: int = 0

                        def __ror__(self, other):  # See docstring of `TestRor`
                            return super().__ror__(other)

                a, b, c = A.Args(1), B.Args(2), C.Args(3)
                assert a | b == RenderArgs(B, a, b)
                assert a | c == RenderArgs(C, a, c)

            def test_incompatible_render_cls(self):
                class B(Renderable):
                    class Args(RenderArgs.Namespace):
                        b: int = 0

                class C(Renderable):
                    class Args(B.Args, inherit=False):
                        c: int = 0

                        def __ror__(self, other):  # See docstring of `TestRor`
                            return super().__ror__(other)

                b, c = B.Args(2), C.Args(3)
                with pytest.raises(IncompatibleArgsNamespaceError):
                    b | c

        class TestRenderArgs:
            class A(Renderable):
                class Args(RenderArgs.Namespace):
                    a: int = 0

            class B(A):
                class Args(RenderArgs.Namespace):
                    b: int = 0

            class C(A):
                class Args(RenderArgs.Namespace):
                    c: int = 0

            # Render class of *other* is a child of that of *self*
            def test_compatible_child_render_cls(self):
                A, B, C = self.A, self.B, self.C
                a, b, c = A.Args(1), B.Args(2), C.Args(3)

                assert RenderArgs(B, b) | a == RenderArgs(B, a, b)
                assert RenderArgs(C, c) | a == RenderArgs(C, a, c)

            # Render class of *other* is a parent of that of *self*
            def test_compatible_parent_render_cls(self):
                A, B, C = self.A, self.B, self.C
                a, b, c = A.Args(1), B.Args(2), C.Args(3)

                assert RenderArgs(A, a) | b == RenderArgs(B, a, b)
                assert RenderArgs(A, a) | c == RenderArgs(C, a, c)

            def test_incompatible_render_cls(self):
                B, C = self.B, self.C
                b, c = B.Args(2), C.Args(3)

                with pytest.raises(IncompatibleRenderArgsError):
                    RenderArgs(C) | b

                with pytest.raises(IncompatibleRenderArgsError):
                    RenderArgs(B) | c

    def test_as_dict(self):
        namespace = self.Namespace()
        assert namespace.as_dict() == dict(foo="FOO", bar="BAR")

        namespace = self.Namespace("bar", "foo")
        assert namespace.as_dict() == dict(foo="bar", bar="foo")

    def test_get_fields(self):
        namespace = self.Namespace()
        assert self.Namespace.get_fields() == dict(foo="FOO", bar="BAR")
        assert namespace.get_fields() == dict(foo="FOO", bar="BAR")

    class TestToRenderArgs:
        class Bar(Foo):
            class Args(RenderArgs.Namespace):
                bar: str = "BAR"

        class Baz(Bar):
            class Args(RenderArgs.Namespace):
                baz: str = "BAZ"

        args_default = Bar.Args()
        args = Bar.Args("bar")

        def test_default(self):
            assert self.args_default.to_render_args() == RenderArgs(self.Bar)
            assert self.args_default.to_render_args(None) == RenderArgs(self.Bar)

            assert self.args.to_render_args() == RenderArgs(self.Bar, self.args)
            assert self.args.to_render_args(None) == RenderArgs(self.Bar, self.args)

        def test_compatible(self):
            assert self.args_default.to_render_args(self.Bar) == RenderArgs(self.Bar)
            assert self.args_default.to_render_args(self.Baz) == RenderArgs(self.Baz)

            assert self.args.to_render_args(self.Bar) == RenderArgs(self.Bar, self.args)
            assert self.args.to_render_args(self.Baz) == RenderArgs(self.Baz, self.args)

        def test_incompatible(self):
            with pytest.raises(IncompatibleArgsNamespaceError):
                self.args_default.to_render_args(Foo)

            with pytest.raises(IncompatibleArgsNamespaceError):
                self.args.to_render_args(Foo)

    def test_update(self):
        namespace = self.Namespace()

        assert namespace.update().as_dict() == dict(foo="FOO", bar="BAR")
        assert namespace.update(foo="bar").as_dict() == dict(foo="bar", bar="BAR")
        assert namespace.update(bar="foo").as_dict() == dict(foo="FOO", bar="foo")
        assert namespace.update(foo="bar", bar="foo").as_dict() == dict(
            foo="bar", bar="foo"
        )

        with pytest.raises(UnknownArgsFieldError, match="'baz'"):
            namespace.update(baz=Ellipsis)


class TestRenderData:
    foo_render_data = RenderData(Foo)

    def test_base(self):
        render_data = RenderData(Renderable)
        assert render_data.render_cls is Renderable
        assert isinstance(render_data[Renderable], Renderable._Data_)

    def test_render_cls(self):
        assert self.foo_render_data.render_cls is Foo

    def test_finalized(self):
        render_data = RenderData(Foo)
        assert render_data.finalized is False

        render_data[Foo].update(foo="FOO", bar="BAR")
        assert render_data.finalized is False

        render_data.finalize()
        assert render_data.finalized is True

    def test_getitem(self):
        class Bar(Foo):
            pass

        class Baz(Bar):
            pass

        render_data = RenderData(Bar)

        with pytest.raises(TypeError, match="'render_cls'"):
            render_data[Ellipsis]

        with pytest.raises(TypeError, match="'render_cls'"):
            render_data[[]]

        with pytest.raises(NoDataNamespaceError):
            render_data[Bar]

        with pytest.raises(ValueError, match="'Bar' is not a subclass of 'Baz'"):
            render_data[Baz]

        assert isinstance(render_data[Foo], Foo._Data_)
        assert isinstance(render_data[Renderable], Renderable._Data_)

    # Currently depends on implementation detail (the order or namespaces) but I don't
    # really see any reasonable/neat way around that for now
    def test_iter(self):
        class A(Renderable):
            class _Data_(RenderData.Namespace):
                foo: None = None

        class B(A):
            class _Data_(RenderData.Namespace):
                foo: None = None

        class C(B):
            class _Data_(RenderData.Namespace):
                foo: None = None

        a_data, base_data = tuple(RenderData(A))
        assert isinstance(a_data, A._Data_)
        assert isinstance(base_data, Renderable._Data_)

        b_data, a_data, base_data = tuple(RenderData(B))
        assert isinstance(a_data, A._Data_)
        assert isinstance(b_data, B._Data_)
        assert isinstance(base_data, Renderable._Data_)

        c_data, b_data, a_data, base_data = tuple(RenderData(C))
        assert isinstance(a_data, A._Data_)
        assert isinstance(b_data, B._Data_)
        assert isinstance(c_data, C._Data_)
        assert isinstance(base_data, Renderable._Data_)

    def test_finalize(self):
        render_data = RenderData(Foo)
        render_data[Foo].update(foo="FOO", bar="BAR")
        assert render_data[Foo].foo == "FOO"
        assert render_data[Foo].bar == "BAR"

        render_data.finalize()
        assert render_data[Foo].foo == "FOO"
        assert render_data[Foo].bar == "FOO"

        # Calls `_finalize_render_data_` only the first time

        render_data[Foo].foo = "bar"
        assert render_data[Foo].foo == "bar"
        assert render_data[Foo].bar == "FOO"

        render_data.finalize()
        assert render_data[Foo].foo == "bar"
        assert render_data[Foo].bar == "FOO"


class TestDataNamespace:
    class Bar(Renderable):
        class _Data_(RenderData.Namespace):
            foo: str
            bar: str

    Namespace = Bar._Data_

    class TestGetattrAndSetattr:
        class Bar(Renderable):
            class _Data_(RenderData.Namespace):
                foo: str
                bar: str

        Namespace = Bar._Data_

        def test_known(self):
            namespace = self.Namespace()
            with pytest.raises(UninitializedDataFieldError, match="'foo' of 'Bar'"):
                namespace.foo
            with pytest.raises(UninitializedDataFieldError, match="'bar' of 'Bar'"):
                namespace.bar

            namespace.foo = "FOO"
            assert namespace.foo == "FOO"
            with pytest.raises(UninitializedDataFieldError, match="'bar' of 'Bar'"):
                namespace.bar

            namespace.bar = "BAR"
            assert namespace.foo == "FOO"
            assert namespace.bar == "BAR"

            namespace.foo = "bar"
            namespace.bar = "foo"
            assert namespace.foo == "bar"
            assert namespace.bar == "foo"

        def test_unknown_get(self):
            namespace = self.Namespace()
            with pytest.raises(UnknownDataFieldError, match="'baz' for 'Bar'"):
                namespace.baz

        def test_unknown_set(self):
            namespace = self.Namespace()
            with pytest.raises(UnknownDataFieldError, match="'baz' for 'Bar'"):
                namespace.baz = Ellipsis

    def test_as_dict(self):
        namespace = self.Namespace()

        with pytest.raises(UninitializedDataFieldError):
            namespace.as_dict()

        namespace.foo = "FOO"
        with pytest.raises(UninitializedDataFieldError):
            namespace.as_dict()

        namespace.bar = "BAR"
        assert namespace.as_dict() == dict(foo="FOO", bar="BAR")

        namespace.foo = "bar"
        namespace.bar = "foo"
        assert namespace.as_dict() == dict(foo="bar", bar="foo")

    def test_get_fields(self):
        namespace = self.Namespace()
        assert self.Namespace.get_fields() == ("foo", "bar")
        assert namespace.get_fields() == ("foo", "bar")

    class TestUpdate:
        class Bar(Renderable):
            class _Data_(RenderData.Namespace):
                foo: str
                bar: str

        Namespace = Bar._Data_

        def test_known(self):
            namespace = self.Namespace()
            with pytest.raises(UninitializedDataFieldError):
                namespace.foo
            with pytest.raises(UninitializedDataFieldError):
                namespace.bar

            namespace.update()
            with pytest.raises(UninitializedDataFieldError):
                namespace.foo
            with pytest.raises(UninitializedDataFieldError):
                namespace.bar

            namespace.update(foo="FOO")
            assert namespace.foo == "FOO"
            with pytest.raises(UninitializedDataFieldError):
                namespace.bar

            namespace.update(bar="BAR")
            assert namespace.as_dict() == dict(foo="FOO", bar="BAR")

            namespace.update()
            assert namespace.as_dict() == dict(foo="FOO", bar="BAR")

            namespace.update(foo="bar", bar="foo")
            assert namespace.as_dict() == dict(foo="bar", bar="foo")

        def test_unknown(self):
            namespace = self.Namespace()
            with pytest.raises(UnknownDataFieldError, match=r"\('baz',\) for 'Bar'"):
                namespace.update(baz=Ellipsis)
