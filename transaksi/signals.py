from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.timezone import localtime
from .models import Transaksi
from laporan.models import ArusKasReport, DetailArusKas
from decimal import Decimal


@receiver(post_save, sender=Transaksi)
def handle_transaksi_Lunas(sender, instance, created, **kwargs):
    if instance.status != "Lunas":
        return

    waktu = localtime(instance.created_at)
    bulan = waktu.month
    tahun = waktu.year

    report, _ = ArusKasReport.objects.get_or_create(
        toko=instance.toko,
        bulan=bulan,
        tahun=tahun,
        defaults={"total_inflow": 0, "total_outflow": 0, "saldo": 0},
    )

    if instance.transaction_type.lower() in ["pemasukan"]:
        jenis = "inflow"
    else:
        jenis = "outflow"

    DetailArusKas.objects.create(
        report=report,
        transaksi=instance,
        jenis=jenis,
        nominal=instance.amount,
        kategori=instance.category,
        tanggal_transaksi=instance.created_at,
        keterangan=f"Transaksi {instance.category}",
    )

    if jenis == "inflow":
        report.total_inflow += Decimal(str(instance.amount))
    else:
        report.total_outflow += Decimal(str(instance.amount))

    report.saldo = report.total_inflow - report.total_outflow
    report.save()
