from fastapi import FastAPI, Path, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, computed_field
from typing import Annotated, Literal , Optional
import json 
from redis_client import redis_client
import logging

app = FastAPI()


logging.basicConfig(
    level=logging.INFO,
    format=" %(levelname)s - %(message)s - %(asctime)s"
)
logger = logging.getLogger(__name__)




class Patient(BaseModel):
    id: Annotated[str , Field(..., description="ID of the Patient" , example='P001')]
    name: Annotated[str , Field(..., description="Name of the Patient")]
    city: Annotated[str, Field(..., description="Name of the City where the patient lives")]
    age: Annotated[int , Field(..., description="Age of the Patient" , ge=0)]
    gender: Annotated[Literal['Male', 'Female', 'Other'] , Field(..., description="Gender of the Patient")]
    height: Annotated[float, Field(..., description="Height of the Patient in meters" , gt=0)]
    weight: Annotated[float, Field(..., description="Weight of the Patient in kilograms" , gt=0)]

    @computed_field
    @property
    def bmi(self) -> float:
        bmi = round(self.weight / (self.height ** 2) , 2)
        return bmi
    
    @computed_field
    @property
    def verdict(self) ->str:
        if self.bmi < 18.5:
            return 'Underweight'
        elif 18.5 <= self.bmi < 25:
            return 'Normal weight'
        elif 25 <= self.bmi < 30:
            return 'Overweight'
        else:
            return 'Obese'
        

class PatientUpdate(BaseModel):
    name: Annotated[Optional[str] , Field(default=None)]
    city: Annotated[Optional[str], Field(default=None)]
    age: Annotated[Optional[int] , Field(default=None , ge=0)]
    gender: Annotated[Optional[Literal['Male', 'Female', 'Other']] , Field(default=None)]
    height: Annotated[Optional[float], Field(default=None , gt=0)]
    weight: Annotated[Optional[float], Field(default=None , gt=0)]


def load_data():
    with open('patients.json' , 'r') as f:
        data = json.load(f)

    return data

def save_data(data):
    with open('patients.json' , 'w') as f:
        json.dump(data, f, indent=4)




def calculate_analytics(data):
    patients = list(data.values())
    total_patients = len(patients)

    if total_patients == 0:
        return {
            "total_patients": 0,
            "average_age": 0,
            "average_bmi": 0,
            "underweight": 0,
            "normal_weight": 0,
            "overweight": 0,
            "obese": 0
        }

    average_age = round(sum(patient["age"] for patient in patients) / total_patients, 2)
    average_bmi = round(sum(patient["bmi"] for patient in patients) / total_patients, 2)
    underweight = sum(1 for patient in patients if patient["verdict"] == "Underweight")
    normal_weight = sum(1 for patient in patients if patient["verdict"] == "Normal weight")
    overweight = sum(1 for patient in patients if patient["verdict"] == "Overweight")
    obese = sum(1 for patient in patients if patient["verdict"] == "Obese")

    return {
        "total_patients": total_patients,
        "average_age": average_age,
        "average_bmi": average_bmi,
        "underweight": underweight,
        "normal_weight": normal_weight,
        "overweight": overweight,
        "obese": obese
    }




@app.get("/")
def root():
    return {'message': 'Patient Management System API.'}


@app.get("/about")
def about():
    return {'message': 'A fully functional API to manage Patients Records.'}


@app.get("/view_patient")
def view():
    cache_key = "all_patients"

    # Try to fetch all patients from Redis
    cached_data = redis_client.get(cache_key)
    if cached_data:
        logger.info("Cache Hit: Returning all patients from Redis")
        return json.loads(cached_data)
    logger.info("Cache Miss: Loading all patients from JSON file")

    # Load patient data
    data = load_data()

    # Cache all patients
    redis_client.set(cache_key, json.dumps(data))
    logger.info("All patients cached successfully.")

    return data



@app.get("/view_patient/{patient_id}")
def view_patient(patient_id: str = Path(..., description="ID of the Patient", example="P001")):
    cache_key = f"patient:{patient_id}"

    # Try to fetch patient from Redis
    cached_data = redis_client.get(cache_key)

    if cached_data:
        logger.info(f"Cache Hit: Patient {patient_id} returned from Redis.")
        return json.loads(cached_data)

    logger.info(f"Cache Miss: Loading Patient {patient_id} from JSON file.")

    # Load patient data from JSON
    data = load_data()

    # Check if patient exists
    if patient_id not in data:
        logger.warning(f"Patient {patient_id} not found.")
        raise HTTPException(
            status_code = 404,
            detail = "Patient Not Found!"
        )

    # Store patient in Redis
    redis_client.set(cache_key, json.dumps(data[patient_id]))
    logger.info(f"Patient {patient_id} cached successfully.")
    return data[patient_id]




@app.get("/sort_patients")
def sort_patients(sort_by: str = Query(..., description="Sort on the basis of height , weight , bmi"), 
                order:str = Query('asc' , description="Sort in Ascending (asc) or Descending Order (desc)", example='asc')
                ):
    
    sort_by = sort_by.lower()
    order = order.lower()
    valid_fields = ['height', 'weight', 'bmi']

    if sort_by not in valid_fields:
        logger.warning(f"Invalid sort field: {sort_by}")
        raise HTTPException(
            status_code=400, 
            detail = f'Invalid field, Select from {valid_fields}'
            )
    if order not in ['asc' , 'desc']:
        logger.warning(f"Invalid sort order: {order}")
        raise HTTPException(
            status_code=400, 
            detail = 'Invalid order, select between Ascending (asc) or Descending (desc)'
            )
    
    # Try to fetch all patients from Redis
    cache_key = "all_patients"
    cached_data = redis_client.get(cache_key)

    if cached_data:
        logger.info("Cache Hit: Loading all patients from Redis")
        data = json.loads(cached_data)
    else:
        logger.info("Cache Miss: Loading all patients from JSON file")
        data = load_data()
        redis_client.set(cache_key, json.dumps(data))
        logger.info("All Patients cached successfully.")

    # Sort the data
    sort_order = order == 'desc'
    sorted_data = sorted(data.values(), key = lambda patient: patient.get(sort_by , 0), reverse = sort_order)
    logger.info(f"Patients sorted by {sort_by} in {order} order.")

    return sorted_data




@app.get("/analytics")
def hospital_analytics():
    analytics_cache_key = "hospital_analytics"
    cached_data = redis_client.get(analytics_cache_key)

    if cached_data:
        logger.info("Cache Hit: Returning analytics from Redis")
        return json.loads(cached_data)

    logger.info("Cache Miss: Calculating analytics from JSON file")

    data = load_data()

    analytics = calculate_analytics(data)
    redis_client.set(analytics_cache_key, json.dumps(analytics))
    logger.info("Hospital analytics cached successfully.")

    return analytics




@app.post("/create")
def create_patient(patient: Patient):

    data = load_data()
    # Check if patient already exists
    if patient.id in data:
        logger.warning(f"Patient {patient.id} already exists.")
        raise HTTPException(
            status_code  = 400,
            detail = f"Patient {patient.id} already exists!"
        )
    # Add patient to json data
    data[patient.id] = patient.model_dump(exclude = ['id'])
    save_data(data)

    patient_cache_key = f"patient:{patient.id}"
    redis_client.set(patient_cache_key, json.dumps(data[patient.id]))
    logger.info(f"Patient {patient.id} cached successfully")
    
    all_patients_cache_key = "all_patients"
    redis_client.set(all_patients_cache_key, json.dumps(data))
    logger.info("All Patients cached updated successfully.")

    analytics_cache_key = "hospital_analytics"
    analytics = calculate_analytics(data)
    redis_client.set(analytics_cache_key, json.dumps(analytics))
    logger.info("Hospital analytics cache updated successfully.")

    return JSONResponse(
        status_code = 201,
        content = {"message": f"Patient {patient.id} created successfully!"}
    )




@app.put("/edit/{patient_id}")
def update_patient(patient_id: str, patient_update: PatientUpdate):

    data = load_data()

    if patient_id not in data:
        logger.warning(f"Patient {patient_id} not found.")
        raise HTTPException(
            status_code=404, 
            detail=f"Patient {patient_id} not found!"
            )
    
    existing_patient_info = data[patient_id]
    update_patient_info = patient_update.model_dump(exclude_unset=True)

    for key, value in update_patient_info.items():
        existing_patient_info[key] = value

    existing_patient_info['id'] = patient_id
    patient_pydantic_obj = Patient(**existing_patient_info)
    existing_patient_info = patient_pydantic_obj.model_dump(exclude=['id'])

    data[patient_id] = existing_patient_info
    save_data(data)

    # Update patient cache
    patient_cache_key = f"patient:{patient_id}"
    redis_client.set(patient_cache_key, json.dumps(existing_patient_info))
    logger.info(f"Patient {patient_id} cache updated successfully.")

    # Update all patients cache
    all_patients_cache_key = "all_patients"
    redis_client.set(all_patients_cache_key, json.dumps(data))
    logger.info("All Patients cache updated successfully")

    # Update hospital analytics cache
    analytics_cache_key = "hospital_analytics"
    analytics = calculate_analytics(data)
    redis_client.set(analytics_cache_key, json.dumps(analytics))
    logger.info("Hospital analytics cache updated successfully.")

    return JSONResponse(
        status_code=200, 
        content={"message": f"Patient {patient_id} updated successfully!"}
        )




@app.delete("/delete/{patient_id}")
def delete_patient(patient_id: str):

    data = load_data()

    if patient_id not in data:
        logger.warning(f"Patient {patient_id} not found.")
        raise HTTPException(
            status_code=404, 
            detail=f"Patient with ID {patient_id} not found!"
            )
    
    del data[patient_id]
    save_data(data)

    patient_cache_key = f"patient:{patient_id}"
    redis_client.delete(patient_cache_key)
    logger.info(f"Patient {patient_id} cache deleted successfully")

    all_patients_cache_key = "all_patients"
    redis_client.set(all_patients_cache_key, json.dumps(data))
    logger.info("All Patients cache updated successfully")

    # Update hospital analytics cache
    analytics_cache_key = "hospital_analytics"
    analytics = calculate_analytics(data)
    redis_client.set(analytics_cache_key, json.dumps(analytics))
    logger.info("Hospital analytics cache updated successfully.")

    return JSONResponse(
        status_code=200, 
        content={"message": f"Patient {patient_id} deleted successfully!"}
        )



