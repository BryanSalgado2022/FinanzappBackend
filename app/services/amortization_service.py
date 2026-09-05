from decimal import ROUND_HALF_UP, Decimal

from app.models.concepto import PeriodoTasa

CENTS = Decimal("0.01")


def tasa_mensual_desde(tasa_interes: Decimal, periodo: PeriodoTasa) -> Decimal:
    """tasa_interes is a percentage (e.g. 27.70 meaning 27.70%)."""
    tasa_fraccion = tasa_interes / Decimal(100)
    if periodo == PeriodoTasa.MENSUAL:
        return tasa_fraccion
    # Effective annual -> effective monthly (matches how Colombian banks quote
    # E.A. rates): (1 + i_anual)^(1/12) - 1. Fractional exponent isn't
    # representable in Decimal arithmetic, so this one step uses float.
    mensual = (1 + float(tasa_fraccion)) ** (1 / 12) - 1
    return Decimal(str(mensual))


def calcular_cuota_fija(principal: Decimal, tasa_mensual: Decimal, numero_cuotas: int) -> Decimal:
    if tasa_mensual == 0:
        cuota = principal / numero_cuotas
    else:
        factor = (1 + tasa_mensual) ** numero_cuotas
        cuota = principal * tasa_mensual * factor / (factor - 1)
    return cuota.quantize(CENTS, rounding=ROUND_HALF_UP)


def calcular_cuotas_restantes(principal: Decimal, tasa_mensual: Decimal, cuota_fija: Decimal) -> int:
    """The inverse of calcular_cuota_fija: given a fixed installment and a
    remaining principal, how many installments (at that same fixed payment)
    are needed to pay it off. Simulates the same per-period interest/capital
    split generar_tabla_amortizacion uses, rather than a closed-form log
    formula, to stay consistent with the rest of this module (Decimal only,
    no new float usage). Used for 'reducir plazo' principal prepayments:
    the cuota stays the same, the term shortens - see design.md."""
    if tasa_mensual == 0:
        cuotas = principal / cuota_fija
        entero = int(cuotas)
        return entero if Decimal(entero) == cuotas else entero + 1

    saldo = principal
    numero = 0
    while saldo > 0:
        interes = (saldo * tasa_mensual).quantize(CENTS, rounding=ROUND_HALF_UP)
        if cuota_fija <= interes:
            raise ValueError(
                "cuota_fija does not cover the interest on this balance; "
                "cannot shorten the term at this payment amount"
            )
        abono_capital = cuota_fija - interes
        saldo = saldo - abono_capital
        numero += 1
        if numero > 1200:
            raise ValueError("could not determine a reasonable number of installments")
    return numero


def generar_tabla_amortizacion(
    principal: Decimal, tasa_mensual: Decimal, numero_cuotas: int
) -> list[dict]:
    """French-method (fixed installment) amortization schedule. The final
    installment absorbs any rounding drift so the ending balance is exactly
    zero, per design.md."""
    cuota = calcular_cuota_fija(principal, tasa_mensual, numero_cuotas)
    saldo = principal
    tabla = []
    for numero in range(1, numero_cuotas + 1):
        interes = (saldo * tasa_mensual).quantize(CENTS, rounding=ROUND_HALF_UP)
        if numero == numero_cuotas:
            abono_capital = saldo
        else:
            abono_capital = cuota - interes
        saldo = saldo - abono_capital
        tabla.append(
            {
                "numero": numero,
                "cuota": interes + abono_capital,
                "interes": interes,
                "abono_capital": abono_capital,
                "saldo": saldo if saldo > 0 else Decimal("0.00"),
            }
        )
    return tabla
