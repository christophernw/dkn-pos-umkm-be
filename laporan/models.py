from django.db import models
from authentication.models import Toko
from django.utils import timezone

class HutangPiutangReport(models.Model):
    id = models.AutoField(primary_key=True)
    toko = models.ForeignKey(Toko, on_delete=models.CASCADE, related_name="hutang_piutang_reports")
    total_hutang = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_piutang = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    jumlah_transaksi_hutang = models.IntegerField(default=0)
    jumlah_transaksi_piutang = models.IntegerField(default=0)
    tanggal = models.DateField(default=timezone.now)
    
    class Meta:
        ordering = ['-tanggal']
        unique_together = ['toko', 'tanggal']
        
    def __str__(self):
        return f"Laporan Hutang Piutang {self.toko.nama} - {self.tanggal}"

class DetailHutangPiutang(models.Model):
    id = models.AutoField(primary_key=True)
    report = models.ForeignKey(HutangPiutangReport, on_delete=models.CASCADE, related_name="details")
    transaksi_id = models.CharField(max_length=10)
    jenis = models.CharField(max_length=10, choices=[('hutang', 'Hutang'), ('piutang', 'Piutang')])
    jumlah = models.DecimalField(max_digits=12, decimal_places=2)
    tanggal_transaksi = models.DateTimeField()
    keterangan = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        ordering = ['-tanggal_transaksi']
        
    def __str__(self):
        return f"{self.jenis.capitalize()} - {self.transaksi_id} - {self.jumlah}"