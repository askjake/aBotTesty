import { PlatformEnum } from '@/enums/beta-reports.enum';
import { PaginationProps } from '@shared/ui/types/pagination.types';

export type BetaReportType = {
  id: number;
  report_display_id: string;
  url: string;
  ingest_date: string;
  platform: PlatformEnum;
  release: number | null;
  release_name: string | null;
  receiver_id: string | null;
  hopper_model: string | null;
  hopperp_model: string | null;
  joey_model: string | null;
  hopperp_id: string | null;
  joey_id: string | null;
  hopper_software: string | null;
  hopperp_software: string | null;
  joey_software: string | null;
  event_date: string;
  event_time: string;
  title: string;
  detail: string;
  marked_log: boolean | null;
  has_attachment: boolean | null;
  category: string | null;
  analysis: string;
  formalized_report: string;
  related_issue: string | null;
};

export type IssueCandidateType = {
  id: string;
  platform: PlatformEnum;
  title: string;
  description: string;
  priority: number;
  date: string;
  last_updated_date: string;
  accepted: boolean | null;
};

export type ReportsReleaseType = {
  id: number;
  release_date: Date;
  release: string;
};

export type BetaReportsProps = {
  start_date?: string;
  end_date?: string;
  release?: number;
  platform?: string;
  device?: string;
};

export type BetaReportsPaginationProps = PaginationProps & BetaReportsProps;

export type IssueCandidatesProps = {
  start_date?: string;
  end_date?: string;
  release?: number;
  platform?: string;
  min_priority?: number;
  max_priority?: number;
};

export type IssueCandidatesPaginationProps = PaginationProps &
  IssueCandidatesProps;

export type ReportsReleasesProps = {
  start_date?: string;
  end_date?: string;
  platform?: string;
};

export type ReportsReleasesPaginationProps = PaginationProps &
  ReportsReleasesProps;
