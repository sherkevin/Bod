# Task: Equipment Management

## Overview

Implement equipment recognition using VLM (Vision Language Model) and equipment inventory management features.

## Dependencies

- Requires `auth-system` to be completed

## Deliverables

### 1. Backend Implementation

#### `services/equipment_service.py`
```python
import os
from typing import List
from sqlalchemy.orm import Session
from app.models.equipment import UserEquipment
from app.services.vlm import VLMService
from app.schemas.equipment import EquipmentCreate, EquipmentResponse

class EquipmentService:
    def __init__(self, db: Session):
        self.db = db
        self.vlm = VLMService()

    async def recognize_from_image(self, user_id: str, image_data: bytes) -> List[dict]:
        """
        Send image to VLM for equipment recognition
        Returns list of recognized equipment
        """
        prompt = """
        Analyze this image and identify all gym equipment visible.
        For each equipment, provide:
        1. name (e.g., "dumbbell", "barbell", "treadmill")
        2. category (free_weight, machine, cardio, functional)
        3. estimated quantity if visible

        Respond in JSON format with a "equipment" array.
        """

        result = await self.vlm.analyze_image(image_data, prompt)
        return result.get("equipment", [])

    def get_user_equipment(self, user_id: str) -> List[UserEquipment]:
        return (
            self.db.query(UserEquipment)
            .filter(UserEquipment.user_id == user_id)
            .order_by(UserEquipment.category, UserEquipment.name)
            .all()
        )

    def add_equipment(self, user_id: str, data: EquipmentCreate) -> UserEquipment:
        # Check for duplicates
        existing = (
            self.db.query(UserEquipment)
            .filter(
                UserEquipment.user_id == user_id,
                UserEquipment.name == data.name,
            )
            .first()
        )
        if existing:
            existing.quantity += data.quantity
            existing.is_available = True
            self.db.commit()
            self.db.refresh(existing)
            return existing

        equipment = UserEquipment(
            user_id=user_id,
            name=data.name,
            category=data.category,
            weight_range=data.weight_range,
            quantity=data.quantity,
            image_url=data.image_url,
        )
        self.db.add(equipment)
        self.db.commit()
        self.db.refresh(equipment)
        return equipment

    def update_equipment(
        self, user_id: str, equipment_id: str, data: dict
    ) -> UserEquipment:
        equipment = (
            self.db.query(UserEquipment)
            .filter(
                UserEquipment.id == equipment_id,
                UserEquipment.user_id == user_id,
            )
            .first()
        )
        if not equipment:
            raise NotFoundException("Equipment not found")

        for key, value in data.items():
            if hasattr(equipment, key):
                setattr(equipment, key, value)

        self.db.commit()
        self.db.refresh(equipment)
        return equipment

    def delete_equipment(self, user_id: str, equipment_id: str) -> None:
        equipment = (
            self.db.query(UserEquipment)
            .filter(
                UserEquipment.id == equipment_id,
                UserEquipment.user_id == user_id,
            )
            .first()
        )
        if not equipment:
            raise NotFoundException("Equipment not found")

        self.db.delete(equipment)
        self.db.commit()

    def get_equipment_by_category(
        self, user_id: str, category: str
    ) -> List[UserEquipment]:
        return (
            self.db.query(UserEquipment)
            .filter(
                UserEquipment.user_id == user_id,
                UserEquipment.category == category,
            )
            .all()
        )
```

#### `services/vlm.py` - VLM Service Wrapper
```python
import httpx
from app.config import settings

class VLMService:
    def __init__(self):
        self.base_url = os.getenv("VLM_URL", "http://vllm:8000")

    async def analyze_image(self, image_bytes: bytes, prompt: str) -> dict:
        """
        Send image to VLM for analysis
        """
        import base64

        image_b64 = base64.b64encode(image_bytes).decode()

        payload = {
            "model": "qwen-vl-chat",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}
                        }
                    ]
                }
            ],
            "response_format": {"type": "json_object"}
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload
            )
            response.raise_for_status()
            result = response.json()

        # Parse response
        content = result["choices"][0]["message"]["content"]
        return json.loads(content)
```

#### `api/v1/equipment.py`
```python
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.services.equipment_service import EquipmentService
from app.schemas.equipment import EquipmentCreate, EquipmentResponse

router = APIRouter(prefix="/equipment", tags=["equipment"])

@router.post("/recognize")
async def recognize_equipment(
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = EquipmentService(db)
    image_data = await image.read()
    recognized = await service.recognize_from_image(current_user.id, image_data)
    return {"equipment": recognized}

@router.get("", response_model=list[EquipmentResponse])
def get_equipment(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = EquipmentService(db)
    return service.get_user_equipment(current_user.id)

@router.post("", response_model=EquipmentResponse)
def add_equipment(
    data: EquipmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = EquipmentService(db)
    return service.add_equipment(current_user.id, data)

@router.patch("/{equipment_id}", response_model=EquipmentResponse)
def update_equipment(
    equipment_id: str,
    updates: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = EquipmentService(db)
    return service.update_equipment(current_user.id, equipment_id, updates)

@router.delete("/{equipment_id}")
def delete_equipment(
    equipment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = EquipmentService(db)
    service.delete_equipment(current_user.id, equipment_id)
    return {"message": "Equipment deleted"}

@router.get("/category/{category}", response_model=list[EquipmentResponse])
def get_by_category(
    category: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = EquipmentService(db)
    return service.get_equipment_by_category(current_user.id, category)
```

### 2. Pydantic Schemas

#### `schemas/equipment.py`
```python
from pydantic import BaseModel, Field
from typing import Optional, Literal

class EquipmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    category: Literal["free_weight", "machine", "cardio", "functional"]
    weight_range: Optional[str] = Field(None, max_length=50)
    quantity: int = Field(1, ge=1)
    image_url: Optional[str] = None

class EquipmentResponse(BaseModel):
    id: str
    user_id: str
    name: str
    category: str
    weight_range: Optional[str]
    quantity: int
    image_url: Optional[str]
    is_available: bool
    created_at: str

    class Config:
        from_attributes = True

class RecognizedEquipment(BaseModel):
    name: str
    category: str
    quantity: Optional[int] = 1
    confidence: Optional[float] = None
```

### 3. Frontend Implementation

#### `app/(main)/equipment/page.tsx`
```typescript
'use client';

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { equipmentApi } from '@/lib/api/equipment';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Camera, Plus, Trash2 } from 'lucide-react';

export default function EquipmentPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const { data: equipment, isLoading } = useQuery({
    queryKey: ['equipment'],
    queryFn: equipmentApi.getEquipment,
  });

  const recognizeMutation = useMutation({
    mutationFn: (file: File) => equipmentApi.recognizeEquipment(file),
    onSuccess: (result) => {
      // Show recognized items for confirmation
    },
  });

  const addMutation = useMutation({
    mutationFn: equipmentApi.addEquipment,
    onSuccess: () => {
      // Refetch equipment list
    },
  });

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleRecognize = async () => {
    if (selectedFile) {
      await recognizeMutation.mutateAsync(selectedFile);
    }
  };

  if (isLoading) return <div>Loading...</div>;

  const grouped = {
    free_weight: equipment?.filter(e => e.category === 'free_weight') || [],
    machine: equipment?.filter(e => e.category === 'machine') || [],
    cardio: equipment?.filter(e => e.category === 'cardio') || [],
    functional: equipment?.filter(e => e.category === 'functional') || [],
  };

  return (
    <div className="container max-w-4xl mx-auto py-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">My Equipment</h1>
        <Button>
          <Camera className="w-4 h-4 mr-2" />
          Take Photo
        </Button>
      </div>

      {/* File Upload for Recognition */}
      <Card className="p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Add Equipment by Photo</h2>
        <input
          type="file"
          accept="image/*"
          onChange={handleFileSelect}
          className="hidden"
          id="photo-input"
        />
        <label htmlFor="photo-input">
          <Button asChild>
            <span>
              <Plus className="w-4 h-4 mr-2" />
              Select Photo
            </span>
          </Button>
        </label>
        {selectedFile && (
          <>
            <p className="mt-2 text-sm text-muted-foreground">
              Selected: {selectedFile.name}
            </p>
            <Button onClick={handleRecognize} className="mt-4">
              Recognize Equipment
            </Button>
          </>
        )}
      </Card>

      {/* Equipment List by Category */}
      {Object.entries(grouped).map(([category, items]) => (
        <div key={category} className="mb-6">
          <h2 className="text-lg font-semibold capitalize mb-3">
            {category.replace('_', ' ')} ({items.length})
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {items.map((item) => (
              <Card key={item.id} className="p-4">
                <div className="font-medium">{item.name}</div>
                {item.weight_range && (
                  <div className="text-sm text-muted-foreground">
                    {item.weight_range}
                  </div>
                )}
                <div className="text-sm">Qty: {item.quantity}</div>
                <Button variant="ghost" size="sm" className="mt-2">
                  <Trash2 className="w-4 h-4" />
                </Button>
              </Card>
            ))}
            {/* Add Manual Button */}
            <Card className="p-4 border-dashed flex items-center justify-center cursor-pointer hover:bg-accent">
              <div className="text-center">
                <Plus className="w-8 h-8 mx-auto mb-2 text-muted-foreground" />
                <span className="text-sm text-muted-foreground">Add Manual</span>
              </div>
            </Card>
          </div>
        </div>
      ))}
    </div>
  );
}
```

#### `lib/api/equipment.ts`
```typescript
import api from '@/lib/api';

export interface Equipment {
  id: string;
  user_id: string;
  name: string;
  category: 'free_weight' | 'machine' | 'cardio' | 'functional';
  weight_range: string | null;
  quantity: number;
  image_url: string | null;
  is_available: boolean;
  created_at: string;
}

export interface RecognizedEquipment {
  name: string;
  category: string;
  quantity?: number;
  confidence?: number;
}

export const equipmentApi = {
  getEquipment: async (): Promise<Equipment[]> => {
    const response = await api.get('/api/v1/equipment');
    return response.data;
  },

  recognizeEquipment: async (file: File): Promise<{ equipment: RecognizedEquipment[] }> => {
    const formData = new FormData();
    formData.append('image', file);
    const response = await api.post('/api/v1/equipment/recognize', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  addEquipment: async (data: {
    name: string;
    category: string;
    weight_range?: string;
    quantity?: number;
    image_url?: string;
  }): Promise<Equipment> => {
    const response = await api.post('/api/v1/equipment', data);
    return response.data;
  },

  updateEquipment: async (id: string, data: Partial<Equipment>): Promise<Equipment> => {
    const response = await api.patch(`/api/v1/equipment/${id}`, data);
    return response.data;
  },

  deleteEquipment: async (id: string): Promise<void> => {
    await api.delete(`/api/v1/equipment/${id}`);
  },
};
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/equipment/recognize` | Upload photo for AI recognition |
| GET | `/api/v1/equipment` | Get user's equipment list |
| POST | `/api/v1/equipment` | Add equipment manually |
| PATCH | `/api/v1/equipment/{id}` | Update equipment |
| DELETE | `/api/v1/equipment/{id}` | Delete equipment |
| GET | `/api/v1/equipment/category/{category}` | Filter by category |

## Technical Requirements

- VLM: Qwen-VL-Chat-Int4 via vLLM
- Image upload max 10MB
- Support JPG, PNG formats
- Camera capture from mobile devices

## Acceptance Criteria

- [ ] User can upload gym photos
- [ ] AI recognizes common equipment accurately (>80%)
- [ ] Recognized items shown for user confirmation
- [ ] User can manually add/edit equipment
- [ ] Equipment grouped by category
- [ ] User can delete equipment
- [ ] Equipment list updates in real-time

## Notes

- VLM prompt engineering is crucial for accuracy
- Consider caching VLM results
- Provide feedback for recognition confidence
- Handle partial recognition gracefully
