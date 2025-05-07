import typing

from models import RoxModel, BaseModel, Field


class PhoneNumber(BaseModel):
    location: typing.Literal["home", "work", "mobile"]
    country_code: str
    number: str


class Person(RoxModel):
    first_name: str
    first_name_two: "str"
    middle_name: typing.Optional[str] = None
    last_name: str
    age: int = Field(
        gt=0,
        le=120,
        description="Age in years",
    )

    phones: typing.List[PhoneNumber] = Field(default_factory=list)

    class Meta:
        class_uuid = "e30c0a66-6ee7-4854-9674-47c66236fb49"


class TableBuilder:

    def build_table(
        self,
        model: typing.Type[RoxModel],
    ) -> None:
        if not issubclass(model, RoxModel):
            raise TypeError("Expected a subclass of RoxModel")

        print(f"Building table for model: {model.Meta.table_name}")
        print("=" * 50)

        fields = model.model_fields
        annotations = typing.get_type_hints(model)
        print(f"annotations = {annotations}")
        for name, field in fields.items():
            print(f"{name}: {field}")
            print(f"  Type: {annotations.get(name, 'Unknown')}")
            print(f"  Default: {field.default!r}")
            print(f"  Default factory: {field.default_factory}")
            print("-" * 50)


if __name__ == "__main__":
    tb = TableBuilder()
    tb.build_table(Person)
