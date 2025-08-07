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
