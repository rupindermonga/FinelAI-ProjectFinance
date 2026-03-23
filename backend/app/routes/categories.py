from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from ..database import get_db
from ..models import CategoryConfig, User
from ..dependencies import get_current_user

router = APIRouter(prefix="/api/categories", tags=["categories"])


# ─── Schemas ─────────────────────────────────────────────────────────────────

class CategoryCreate(BaseModel):
    name: str
    level: str          # "category" | "sub_category" | "sub_division"
    parent_id: Optional[int] = None
    display_order: int = 100
    requires_sub_division: bool = False

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None
    requires_sub_division: Optional[bool] = None

class CategoryOut(BaseModel):
    id: int
    name: str
    level: str
    parent_id: Optional[int]
    is_active: bool
    display_order: int
    requires_sub_division: bool = False
    children: List['CategoryOut'] = []

    class Config:
        from_attributes = True

CategoryOut.model_rebuild()


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _build_tree(items: list) -> list:
    """Convert flat list into nested tree (categories → sub_categories → sub_divisions)."""
    by_id = {item.id: {**CategoryOut.model_validate(item).model_dump(), "children": []} for item in items}
    roots = []
    for item in items:
        node = by_id[item.id]
        if item.parent_id and item.parent_id in by_id:
            by_id[item.parent_id]["children"].append(node)
        else:
            roots.append(node)
    return roots


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.get("")
def list_categories(
    flat: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    flat=false  → nested tree: categories with sub_categories, each with sub_divisions
    flat=true   → flat list (used by Gemini prompt builder)
    """
    items = (
        db.query(CategoryConfig)
        .filter(CategoryConfig.user_id == current_user.id)
        .order_by(CategoryConfig.level, CategoryConfig.display_order, CategoryConfig.name)
        .all()
    )
    if flat:
        return [CategoryOut.model_validate(i) for i in items]
    return _build_tree(items)


@router.get("/active-names")
def get_active_category_names(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns structured active categories for the Gemini prompt."""
    items = (
        db.query(CategoryConfig)
        .filter(CategoryConfig.user_id == current_user.id, CategoryConfig.is_active == True)
        .order_by(CategoryConfig.level, CategoryConfig.display_order)
        .all()
    )
    by_id = {i.id: i for i in items}

    categories = [i for i in items if i.level == "category"]
    result = []
    for cat in categories:
        # Sub-categories are children of the category
        sub_cats = [i.name for i in items if i.level == "sub_category" and i.parent_id == cat.id]
        # Sub-divisions are ALSO direct children of the category (independent of sub-category)
        sub_divs = [i.name for i in items if i.level == "sub_division" and i.parent_id == cat.id]
        result.append({
            "name": cat.name,
            "sub_categories": sub_cats,
            "sub_divisions": sub_divs,
            "requires_sub_division": cat.requires_sub_division,
        })
    return result


@router.post("", response_model=CategoryOut)
def create_category(
    body: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not body.name or not body.name.strip():
        raise HTTPException(status_code=400, detail="name cannot be empty")

    if body.level not in ("category", "sub_category", "sub_division"):
        raise HTTPException(status_code=400, detail="level must be category, sub_category, or sub_division")

    if body.level in ("sub_category", "sub_division") and not body.parent_id:
        raise HTTPException(status_code=400, detail=f"parent_id is required for {body.level}")

    # Validate parent belongs to this user and is the correct level
    if body.parent_id:
        parent = db.query(CategoryConfig).filter(
            CategoryConfig.id == body.parent_id,
            CategoryConfig.user_id == current_user.id
        ).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent category not found")
        # sub_category parent must be a category
        # sub_division parent must ALSO be a category (not sub_category)
        if body.level == "sub_category" and parent.level != "category":
            raise HTTPException(status_code=400, detail="sub_category parent must be a category")
        if body.level == "sub_division" and parent.level != "category":
            raise HTTPException(status_code=400, detail="sub_division parent must be a category (sub-divisions are independent of sub-categories)")

    item = CategoryConfig(
        user_id=current_user.id,
        level=body.level,
        name=body.name,
        parent_id=body.parent_id,
        display_order=body.display_order,
        requires_sub_division=body.requires_sub_division,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{cat_id}", response_model=CategoryOut)
def update_category(
    cat_id: int,
    body: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    item = db.query(CategoryConfig).filter(
        CategoryConfig.id == cat_id,
        CategoryConfig.user_id == current_user.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")

    _ALLOWED = {"name", "is_active", "display_order", "requires_sub_division"}
    for field, value in body.model_dump(exclude_unset=True).items():
        if field in _ALLOWED:
            setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{cat_id}")
def delete_category(
    cat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    item = db.query(CategoryConfig).filter(
        CategoryConfig.id == cat_id,
        CategoryConfig.user_id == current_user.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")

    # cascade deletes children (sub_categories delete sub_divisions too)
    db.delete(item)
    db.commit()
    return {"message": f"Deleted '{item.name}' and all its children"}
