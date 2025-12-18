from django import forms
from .models import AnioEconomico, ConceptoPago, CuentaPorCobrar, Pago
from decimal import Decimal
from datetime import date
from django.core.exceptions import ValidationError

from academico.models import Estudiante


class AnioEconomicoForm(forms.ModelForm):
    class Meta:
        model = AnioEconomico
        fields = ["nombre", "fecha_inicio", "fecha_fin", "activo"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-input"}),
            "fecha_inicio": forms.DateInput(attrs={"type": "date", "class": "form-input"}),
            "fecha_fin": forms.DateInput(attrs={"type": "date", "class": "form-input"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }

    def clean(self):
        cleaned = super().clean()
        fi = cleaned.get("fecha_inicio")
        ff = cleaned.get("fecha_fin")
        if fi and ff and ff < fi:
            self.add_error("fecha_fin", "La fecha fin no puede ser anterior a la fecha inicio.")
        return cleaned

class ConceptoPagoForm(forms.ModelForm):
    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.school = school

        # Select año SOLO del colegio
        if school:
            self.fields["anio"].queryset = AnioEconomico.objects.filter(school=school)

    class Meta:
        model = ConceptoPago
        fields = ["nombre", "descripcion", "anio", "valor", "recurrente", "activo"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-input", "placeholder": "Ej. Pensión"}),
            "descripcion": forms.Textarea(attrs={"class": "form-input", "rows": 3, "placeholder": "Opcional"}),
            "anio": forms.Select(attrs={"class": "form-select"}),
            "valor": forms.NumberInput(attrs={"class": "form-input", "step": "0.01", "min": "0"}),
            "recurrente": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }

    def clean(self):
        cleaned = super().clean()
        nombre = (cleaned.get("nombre") or "").strip()
        anio = cleaned.get("anio")

        if nombre and anio and self.school:
            qs = ConceptoPago.objects.filter(
                school=self.school,
                nombre__iexact=nombre,
                anio=anio
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error("nombre", "Ya existe un concepto con este nombre en el año seleccionado.")

        return cleaned

    def clean_valor(self):
        v = self.cleaned_data.get("valor")
        if v is None or v < 0:
            raise forms.ValidationError("El valor debe ser mayor o igual a 0.")
        return v

class CuentaPorCobrarForm(forms.ModelForm):
    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.school = school

        if school:
            # ✅ Conceptos SOLO del colegio
            self.fields["concepto"].queryset = (
                ConceptoPago.objects
                .select_related("anio")
                .filter(school=school, activo=True)
                .order_by("-anio__activo", "-anio__nombre", "nombre")
            )

            # ✅ Estudiantes SOLO del colegio (AJUSTA el filtro según tu modelo)
            # Si Estudiante tiene school:
            # self.fields["estudiante"].queryset = Estudiante.objects.filter(school=school)
            # Si Estudiante NO tiene school pero Curso sí: estudiante__curso__school
            self.fields["estudiante"].queryset = (
                Estudiante.objects
                .filter(curso__school=school)   # <-- cambia esto si tu relación es distinta
                .order_by("apellidos", "nombres")
            )

    class Meta:
        model = CuentaPorCobrar
        fields = ["estudiante", "concepto", "fecha_vencimiento", "valor_total", "saldo_pendiente", "pagada"]
        widgets = {
            "estudiante": forms.Select(attrs={"class": "form-select"}),
            "concepto": forms.Select(attrs={"class": "form-select"}),
            "fecha_vencimiento": forms.DateInput(attrs={"type": "date", "class": "form-input"}),
            "valor_total": forms.NumberInput(attrs={"class": "form-input", "step": "0.01", "min": "0"}),
            "saldo_pendiente": forms.NumberInput(attrs={"class": "form-input", "step": "0.01", "min": "0"}),
        }

    def clean(self):
        cleaned = super().clean()

        est = cleaned.get("estudiante")
        concepto = cleaned.get("concepto")

        # 🔒 seguridad: estudiante y concepto deben ser del mismo colegio
        if self.school and concepto and concepto.school_id != self.school.id:
            self.add_error("concepto", "Concepto inválido para este colegio.")

        # Ajusta esta validación según tu modelo real:
        if self.school and est:
            # si Estudiante se valida via curso__school
            if getattr(est, "curso", None) and getattr(est.curso, "school_id", None) != self.school.id:
                self.add_error("estudiante", "Estudiante inválido para este colegio.")

        valor = cleaned.get("valor_total") or 0
        saldo = cleaned.get("saldo_pendiente")

        if saldo is None:
            cleaned["saldo_pendiente"] = valor
            saldo = valor

        cleaned["pagada"] = bool(saldo == 0)
        return cleaned


class PagoForm(forms.ModelForm):
    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.school = school

        if school:
            # ✅ Solo cuentas del colegio (por concepto)
            self.fields["cuenta"].queryset = (
                CuentaPorCobrar.objects
                .select_related("concepto", "concepto__anio", "estudiante")
                .filter(concepto__school=school)
                .order_by("-fecha_generacion")
            )

    class Meta:
        model = Pago
        fields = ["cuenta", "medio_pago", "valor_pagado", "observaciones"]
        widgets = {
            "cuenta": forms.Select(attrs={"class": "form-select"}),
            "medio_pago": forms.TextInput(attrs={"class": "form-input", "placeholder": "efectivo, transferencia..."}),
            "valor_pagado": forms.NumberInput(attrs={"class": "form-input", "step": "0.01", "min": "0"}),
            "observaciones": forms.Textarea(attrs={"class": "form-input", "rows": 3}),
        }

    def clean(self):
        cleaned = super().clean()
        cuenta = cleaned.get("cuenta")
        valor_pagado = cleaned.get("valor_pagado")

        if not cuenta or valor_pagado is None:
            return cleaned

        # 🔒 seguridad: cuenta debe pertenecer al colegio
        if self.school and cuenta.concepto.school_id != self.school.id:
            raise ValidationError("Cuenta inválida para este colegio.")

        if self.instance.pk is None:
            if valor_pagado <= 0:
                raise ValidationError("El valor pagado debe ser mayor a 0.")
            if valor_pagado > (cuenta.saldo_pendiente or Decimal("0")):
                raise ValidationError(
                    f"El valor pagado ({valor_pagado}) excede el saldo pendiente ({cuenta.saldo_pendiente})."
                )
        else:
            original = Pago.objects.get(pk=self.instance.pk)
            delta = (valor_pagado or Decimal("0")) - (original.valor_pagado or Decimal("0"))
            if (cuenta.saldo_pendiente or Decimal("0")) - delta < 0:
                raise ValidationError(
                    f"No es posible actualizar: el nuevo valor dejaría saldo negativo. "
                    f"Saldo actual: {cuenta.saldo_pendiente}, delta: {delta}."
                )
            if valor_pagado <= 0:
                raise ValidationError("El valor pagado debe ser mayor a 0.")

        if not cleaned.get("fecha_pago"):
            cleaned["fecha_pago"] = date.today()

        return cleaned