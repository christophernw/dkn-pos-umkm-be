from ninja import Router
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Sum, Count, Q
from transaksi.models import Transaksi
from authentication.models import User
from produk.api import AuthBearer
from datetime import datetime, date, timedelta
from django.utils import timezone
from .models import HutangPiutangReport, DetailHutangPiutang
from .schemas import (
    HutangPiutangSummaryResponse, 
    HutangPiutangDetailResponse,
    TransaksiHutangPiutangDetail,
    DateRangeRequest,
    PaginatedHutangPiutangReportResponse,
    HutangPiutangReportListItem
)

router = Router(auth=AuthBearer())

@router.get("/hutang-piutang/summary", response=HutangPiutangSummaryResponse)
def get_hutang_piutang_summary(request):
    """
    Mendapatkan ringkasan total hutang dan piutang terbaru
    """
    user_id = request.auth
    user = get_object_or_404(User, id=user_id)
    
    if not user.toko:
        return HutangPiutangSummaryResponse(
            total_hutang=0,
            total_piutang=0,
            jumlah_transaksi_hutang=0,
            jumlah_transaksi_piutang=0
        )
    
    # Hutang: transaksi pengeluaran yang belum lunas
    hutang_transaksi = Transaksi.objects.filter(
        toko=user.toko,
        transaction_type="pengeluaran",
        status="Belum Lunas",
        is_deleted=False
    )
    
    # Piutang: transaksi pemasukan yang belum lunas
    piutang_transaksi = Transaksi.objects.filter(
        toko=user.toko,
        transaction_type="pemasukan",
        status="Belum Lunas",
        is_deleted=False
    )
    
    total_hutang = hutang_transaksi.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_piutang = piutang_transaksi.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    jumlah_transaksi_hutang = hutang_transaksi.count()
    jumlah_transaksi_piutang = piutang_transaksi.count()
    
    return HutangPiutangSummaryResponse(
        total_hutang=float(total_hutang),
        total_piutang=float(total_piutang),
        jumlah_transaksi_hutang=jumlah_transaksi_hutang,
        jumlah_transaksi_piutang=jumlah_transaksi_piutang
    )

@router.get("/hutang-piutang/detail", response=HutangPiutangDetailResponse)
def get_hutang_piutang_detail(request, start_date: date = None, end_date: date = None):
    """
    Mendapatkan daftar transaksi hutang dan piutang dengan filter tanggal
    """
    user_id = request.auth
    user = get_object_or_404(User, id=user_id)
    
    if not user.toko:
        return HutangPiutangDetailResponse(hutang=[], piutang=[])
    
    query_hutang = Q(
        toko=user.toko,
        transaction_type="pengeluaran",
        status="Belum Lunas",
        is_deleted=False
    )
    
    query_piutang = Q(
        toko=user.toko,
        transaction_type="pemasukan",
        status="Belum Lunas",
        is_deleted=False
    )
    
    # Tambahkan filter tanggal jika disediakan
    if start_date:
        # Filter by date component of created_at
        query_hutang &= Q(created_at__date__gte=start_date)
        query_piutang &= Q(created_at__date__gte=start_date)
    
    if end_date:
        # Filter by date component of created_at
        query_hutang &= Q(created_at__date__lte=end_date)
        query_piutang &= Q(created_at__date__lte=end_date)
    
    hutang_transaksi = Transaksi.objects.filter(query_hutang).order_by('-created_at')
    piutang_transaksi = Transaksi.objects.filter(query_piutang).order_by('-created_at')
    
    hutang_list = [TransaksiHutangPiutangDetail.from_transaksi(t) for t in hutang_transaksi]
    piutang_list = [TransaksiHutangPiutangDetail.from_transaksi(t) for t in piutang_transaksi]
    
    return HutangPiutangDetailResponse(hutang=hutang_list, piutang=piutang_list)


@router.post("/hutang-piutang/generate", response=dict)
@transaction.atomic
def generate_hutang_piutang_report(request, payload: DateRangeRequest):
    """
    Membuat atau memperbarui laporan hutang piutang untuk rentang tanggal tertentu
    """
    user_id = request.auth
    user = get_object_or_404(User, id=user_id)
    
    if not user.toko:
        return {"message": "User tidak memiliki toko"}
    
    today = timezone.now().date()
    start_date = payload.start_date or today
    end_date = payload.end_date or today
    
    # Pastikan start_date tidak lebih besar dari end_date
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    
    reports_created = 0
    current_date = start_date
    
    # Membuat laporan untuk setiap hari dalam rentang tanggal
    while current_date <= end_date:
        # Hitung hutang (pengeluaran yang belum lunas) untuk tanggal ini
        hutang_transaksi = Transaksi.objects.filter(
            toko=user.toko,
            transaction_type="pengeluaran",
            status="Belum Lunas",
            is_deleted=False,
            created_at__date=current_date
        )
        
        total_hutang = hutang_transaksi.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        jumlah_transaksi_hutang = hutang_transaksi.count()
        
        # Hitung piutang (pemasukan yang belum lunas) untuk tanggal ini
        piutang_transaksi = Transaksi.objects.filter(
            toko=user.toko,
            transaction_type="pemasukan",
            status="Belum Lunas",
            is_deleted=False,
            created_at__date=current_date
        )
        
        total_piutang = piutang_transaksi.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        jumlah_transaksi_piutang = piutang_transaksi.count()
        
        # Buat atau update laporan untuk tanggal ini
        report, created = HutangPiutangReport.objects.update_or_create(
            toko=user.toko,
            tanggal=current_date,
            defaults={
                'total_hutang': total_hutang,
                'total_piutang': total_piutang,
                'jumlah_transaksi_hutang': jumlah_transaksi_hutang,
                'jumlah_transaksi_piutang': jumlah_transaksi_piutang
            }
        )
        
        # Hapus detail lama jika laporan ini diupdate
        if not created:
            report.details.all().delete()
        
        # Tambahkan detail hutang
        for transaksi in hutang_transaksi:
            DetailHutangPiutang.objects.create(
                report=report,
                transaksi_id=transaksi.id,
                jenis='hutang',
                jumlah=transaksi.total_amount,
                tanggal_transaksi=transaksi.created_at,
                keterangan=transaksi.category
            )
        
        # Tambahkan detail piutang
        for transaksi in piutang_transaksi:
            DetailHutangPiutang.objects.create(
                report=report,
                transaksi_id=transaksi.id,
                jenis='piutang',
                jumlah=transaksi.total_amount,
                tanggal_transaksi=transaksi.created_at,
                keterangan=transaksi.category
            )
        
        reports_created += 1
        current_date += timedelta(days=1)
    
    return {"message": f"Berhasil membuat {reports_created} laporan hutang piutang"}

@router.get("/hutang-piutang/reports", response=PaginatedHutangPiutangReportResponse)
def get_hutang_piutang_reports(request, page: int = 1, per_page: int = 10, start_date: date = None, end_date: date = None):
    """
    Mendapatkan daftar laporan hutang piutang dengan paginasi dan filter tanggal
    """
    user_id = request.auth
    user = get_object_or_404(User, id=user_id)
    
    if not user.toko:
        return PaginatedHutangPiutangReportResponse(
            items=[],
            total=0,
            page=page,
            per_page=per_page,
            total_pages=0
        )
    
    query = Q(toko=user.toko)
    
    if start_date:
        query &= Q(tanggal__gte=start_date)
    
    if end_date:
        query &= Q(tanggal__lte=end_date)
    
    queryset = HutangPiutangReport.objects.filter(query).order_by('-tanggal')
    
    total = queryset.count()
    
    # Handle kasus per_page nol
    if per_page <= 0:
        per_page = 10
    
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    
    # Jika page melebihi total_pages, kembali ke halaman 1
    if page > total_pages:
        page = 1
    
    offset = (page - 1) * per_page
    page_items = queryset[offset : offset + per_page]
    
    return PaginatedHutangPiutangReportResponse(
        items=[HutangPiutangReportListItem.from_orm(report) for report in page_items],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )