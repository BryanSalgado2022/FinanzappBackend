from decimal import Decimal

from app.models.concepto import PeriodoTasa
from app.services.amortization_service import (
    calcular_cuota_fija,
    generar_tabla_amortizacion,
    tasa_mensual_desde,
)


def test_tasa_mensual_directa():
    tasa = tasa_mensual_desde(Decimal("2"), PeriodoTasa.MENSUAL)
    assert tasa == Decimal("0.02")


def test_tasa_anual_se_convierte_a_mensual_efectiva():
    # 100% E.A. -> monthly rate is NOT 100%/12; it's (2)^(1/12) - 1 ~= 5.9463%
    tasa = tasa_mensual_desde(Decimal("100"), PeriodoTasa.ANUAL)
    assert Decimal("0.0594") < tasa < Decimal("0.0595")


def test_cuota_fija_sin_interes_es_principal_entre_cuotas():
    cuota = calcular_cuota_fija(Decimal("1200000"), Decimal("0"), 12)
    assert cuota == Decimal("100000.00")


def test_cuota_fija_con_interes_conocida():
    # Textbook example: 1,000,000 at 2% monthly, 12 installments -> ~94,560.19
    cuota = calcular_cuota_fija(Decimal("1000000"), Decimal("0.02"), 12)
    assert Decimal("94500") < cuota < Decimal("94600")


def test_tabla_amortizacion_saldo_final_es_cero():
    tabla = generar_tabla_amortizacion(Decimal("1000000"), Decimal("0.02"), 12)
    assert len(tabla) == 12
    assert tabla[-1]["saldo"] == Decimal("0.00")


def test_tabla_amortizacion_reconciliacion_de_capital():
    principal = Decimal("1000000")
    tabla = generar_tabla_amortizacion(principal, Decimal("0.02"), 12)
    total_abonado = sum((row["abono_capital"] for row in tabla), Decimal("0"))
    assert total_abonado == principal


def test_tabla_amortizacion_interes_decrece_con_saldo():
    tabla = generar_tabla_amortizacion(Decimal("1000000"), Decimal("0.02"), 12)
    assert tabla[0]["interes"] > tabla[-1]["interes"]
