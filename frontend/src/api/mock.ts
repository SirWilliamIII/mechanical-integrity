/**
 * Mock Data Service for Development and Testing
 * Provides realistic sample data for frontend development when backend is unavailable
 * 
 * TODO: [FRONTEND_INTEGRATION] Replace mock API calls with real backend endpoints
 * Current issue: 8+ frontend API calls still using placeholder mock data instead of real backend
 * Priority: High - prevents full integration testing and production deployment
 * Implementation needed: Update all API service calls to use actual FastAPI endpoints
 */

import type {
  Equipment,
  InspectionRecord,
  ThicknessReading,
  API579Calculation,
  PaginatedResponse,
  EquipmentType,
  EquipmentStatus,
  InspectionStatus
} from '@/types'

// Mock Equipment Data
export const mockEquipment: Equipment[] = [
  {
    id: 'eq-001',
    tagNumber: 'V-101',
    description: 'Pressure Vessel - Separator',
    equipmentType: 'pressure_vessel' as EquipmentType,
    location: 'Unit 1 - Area A',
    manufacturer: 'ABC Fabricators',
    modelNumber: 'PV-2024-X',
    serialNumber: 'SN123456789',
    yearInstalled: 2018,
    status: 'active' as EquipmentStatus,
    designPressure: 150.0,
    designTemperature: 350.0,
    operatingPressure: 125.0,
    operatingTemperature: 300.0,
    material: 'SA-516 Grade 70',
    nominalThickness: 0.500,
    minimumThickness: 0.375,
    corrosionAllowance: 0.125,
    efficiency: 0.85,
    nextInspectionDate: '2024-12-01',
    lastInspectionDate: '2023-12-01',
    createdAt: '2023-01-15T10:00:00Z',
    updatedAt: '2023-12-01T14:30:00Z'
  },
  {
    id: 'eq-002',
    tagNumber: 'E-201',
    description: 'Heat Exchanger - Shell & Tube',
    equipmentType: 'heat_exchanger' as EquipmentType,
    location: 'Unit 2 - Area B',
    manufacturer: 'XYZ Heat Transfer',
    modelNumber: 'HX-ST-150',
    serialNumber: 'HX987654321',
    yearInstalled: 2020,
    status: 'active' as EquipmentStatus,
    designPressure: 200.0,
    designTemperature: 400.0,
    operatingPressure: 175.0,
    operatingTemperature: 375.0,
    material: 'SA-106 Grade B',
    nominalThickness: 0.375,
    minimumThickness: 0.250,
    corrosionAllowance: 0.125,
    efficiency: 0.90,
    nextInspectionDate: '2025-06-01',
    lastInspectionDate: '2024-06-01',
    createdAt: '2020-03-10T08:00:00Z',
    updatedAt: '2024-06-01T16:45:00Z'
  },
  {
    id: 'eq-003',
    tagNumber: 'P-301A',
    description: 'Centrifugal Pump - Feed Water',
    equipmentType: 'pump' as EquipmentType,
    location: 'Unit 3 - Pump House',
    manufacturer: 'DEF Pumps Inc',
    modelNumber: 'CP-500-A',
    serialNumber: 'P456789123',
    yearInstalled: 2019,
    status: 'maintenance' as EquipmentStatus,
    designPressure: 300.0,
    designTemperature: 250.0,
    operatingPressure: 250.0,
    operatingTemperature: 200.0,
    material: 'Stainless Steel 316L',
    nominalThickness: 0.250,
    minimumThickness: 0.125,
    corrosionAllowance: 0.062,
    efficiency: 0.95,
    nextInspectionDate: '2024-09-15',
    lastInspectionDate: '2023-09-15',
    createdAt: '2019-05-20T12:00:00Z',
    updatedAt: '2024-08-10T11:20:00Z'
  }
]

// Mock Thickness Readings
export const mockThicknessReadings: ThicknessReading[] = [
  {
    cmlNumber: 'CML-V101-01',
    location: 'Shell - Top',
    reading: 0.485,
    previousReading: 0.492,
    metalLoss: 0.007,
    metalLossRate: 0.0035,
    confidenceLevel: 95,
    inspector: 'John Smith',
    inspectionDate: '2024-08-15'
  },
  {
    cmlNumber: 'CML-V101-02',
    location: 'Shell - Bottom',
    reading: 0.478,
    previousReading: 0.487,
    metalLoss: 0.009,
    metalLossRate: 0.0045,
    confidenceLevel: 92,
    inspector: 'John Smith',
    inspectionDate: '2024-08-15'
  },
  {
    cmlNumber: 'CML-V101-03',
    location: 'Head - Inlet',
    reading: 0.495,
    previousReading: 0.498,
    metalLoss: 0.003,
    metalLossRate: 0.0015,
    confidenceLevel: 98,
    inspector: 'John Smith',
    inspectionDate: '2024-08-15'
  }
]

// Mock API 579 Calculations
export const mockAPI579Calculations: API579Calculation[] = [
  {
    id: 'calc-001',
    inspectionId: 'insp-001',
    calculationType: 'Level 1 Assessment',
    remainingStrengthFactor: 0.92,
    remainingLife: 8.5,
    recommendedInspectionInterval: 2.0,
    criticalFindings: [],
    complianceStatus: 'Acceptable',
    calculationDetails: {
      minimumThickness: 0.375,
      actualThickness: 0.478,
      allowableStress: 20000,
      safetyFactor: 2.0,
      futureCorrosionAllowance: 0.125
    },
    calculatedAt: '2024-08-15T10:30:00Z',
    calculatedBy: 'API 579 Engine v2.1'
  }
]

// Mock Inspection Records
export const mockInspectionRecords: InspectionRecord[] = [
  {
    id: 'insp-001',
    equipmentId: 'eq-001',
    equipmentTag: 'V-101',
    inspectionDate: '2024-08-15',
    inspectionType: 'Routine Thickness Survey',
    inspector: 'John Smith',
    inspectorCertification: 'API 510 Inspector #12345',
    status: 'completed' as InspectionStatus,
    thicknessReadings: mockThicknessReadings,
    findings: 'Minor corrosion observed at shell bottom. Within acceptable limits per API 579.',
    recommendations: 'Continue current inspection interval. Monitor CML-V101-02 closely.',
    operatorNotes: 'Equipment cleaned prior to inspection. All access points clear.',
    documents: [
      {
        id: 'doc-001',
        filename: 'V-101_Thickness_Report_2024-08-15.pdf',
        uploadedAt: '2024-08-15T11:00:00Z'
      }
    ],
    api579Calculations: mockAPI579Calculations,
    isVerified: false,
    verifiedBy: null,
    verifiedAt: null,
    createdAt: '2024-08-15T08:00:00Z',
    updatedAt: '2024-08-15T16:30:00Z'
  }
]

// Mock API Responses
export const mockApiResponses = {
  // Equipment endpoints
  getEquipment: (): Promise<PaginatedResponse<Equipment>> => {
    return Promise.resolve({
      data: mockEquipment,
      pagination: {
        page: 1,
        perPage: 100,
        total: mockEquipment.length,
        totalPages: 1
      }
    })
  },

  getEquipmentById: (id: string): Promise<Equipment> => {
    const equipment = mockEquipment.find(eq => eq.id === id)
    if (!equipment) {
      return Promise.reject({ message: 'Equipment not found', status: 404 })
    }
    return Promise.resolve(equipment)
  },

  // Inspection endpoints
  getInspections: (): Promise<PaginatedResponse<InspectionRecord>> => {
    return Promise.resolve({
      data: mockInspectionRecords,
      pagination: {
        page: 1,
        perPage: 100,
        total: mockInspectionRecords.length,
        totalPages: 1
      }
    })
  },

  createInspection: (data: any): Promise<InspectionRecord> => {
    const newInspection: InspectionRecord = {
      id: `insp-${Date.now()}`,
      equipmentId: data.equipmentId || 'eq-001',
      equipmentTag: data.equipmentTag || 'Unknown',
      inspectionDate: data.inspectionDate || new Date().toISOString().split('T')[0],
      inspectionType: data.inspectionType || 'General Inspection',
      inspector: data.inspector || 'Mock Inspector',
      inspectorCertification: data.inspectorCertification || 'API 510',
      status: 'pending' as InspectionStatus,
      thicknessReadings: data.thicknessReadings || [],
      findings: data.findings || '',
      recommendations: data.recommendations || '',
      operatorNotes: data.operatorNotes || '',
      documents: [],
      api579Calculations: [],
      isVerified: false,
      verifiedBy: null,
      verifiedAt: null,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    }
    
    mockInspectionRecords.unshift(newInspection)
    return Promise.resolve(newInspection)
  }
}

// Development mode flag
export const isDevelopmentMode = import.meta.env.DEV
export const useMockData = import.meta.env.VITE_USE_MOCK_DATA === 'true' || isDevelopmentMode