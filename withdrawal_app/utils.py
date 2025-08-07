def paginate(data,success=True,message="All items get successfully.", page=1, per_page=10, max_page_size=100):
    per_page = min(per_page, max_page_size)
    total_items = len(data)
    total_pages = (total_items + per_page - 1) // per_page
    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    paginated_data = data[start_index:end_index]
    
    return {
        "success":success,
        "message":message,
        "data": paginated_data,
        "pagination": {
            "current_page": page,
            "per_page": per_page,
            "total_items": total_items,
            "total_pages": total_pages,
            "next_page": page + 1 if end_index < total_items else None,
            "previous_page": page - 1 if start_index > 0 else None,
        }
    }
    
def mtnr_unit_price(pack_size, unit_tp, unit_vat):
    clean = pack_size.replace("'", "").replace("s", "").lower().replace(" ", "")
    if "x" in clean:
        parts = clean.split("x")
        pack_strip = int(parts[0])
        strip_unit = int(parts[1])
        unit_per_pack = pack_strip * strip_unit
    else:
        unit_per_pack = int(clean)

    unit_price = (float(unit_tp) + float(unit_vat)) / unit_per_pack
    return unit_price

