import { FC, useEffect, useImperativeHandle, useState } from 'react';
import { Card, TableProps } from 'antd';

import useHandleError from '@shared/ui/hooks/useHandleError.hook';
import { getBetaReports } from '@/services/beta-reports.services';
import { DEFAULT_PAGE_SIZE } from '@shared/ui/constants/common.constants';

import {
  StyledReportsTable,
  StyledReportsText,
} from '@/components/organisms/Reports/Reports.styled';

import { BetaReportType } from '@/types/beta-reports.types';
import { ColumnsType } from 'antd/es/table';
import { TableParams } from '@shared/ui/types/common.types';
import { ReportsProps } from '@/components/organisms/Reports/Reports.props';

const columns: ColumnsType<BetaReportType> = [
  {
    title: 'report_id',
    dataIndex: 'report_display_id',
  },
  {
    title: 'url',
    dataIndex: 'url',
    render: (_, { url }) => (
      <a href={url} target='_blank'>
        Open link
      </a>
    ),
  },
  {
    title: 'title',
    dataIndex: 'title',
    width: '250px',
  },
  {
    title: 'event_time',
    dataIndex: 'event_time',
  },
  {
    title: 'category',
    dataIndex: 'category',
  },
  {
    title: 'formalized_report',
    dataIndex: 'formalized_report',
    width: '350px',
    render: (_, { formalized_report }) => (
      <StyledReportsText
        ellipsis={{
          rows: 2,
          expandable: 'collapsible',
        }}
      >
        {formalized_report}
      </StyledReportsText>
    ),
  },
  {
    title: 'user_report',
    dataIndex: 'detail',
    width: '350px',
    render: (_, { detail }) => (
      <StyledReportsText
        ellipsis={{
          rows: 2,
          expandable: 'collapsible',
        }}
      >
        {detail}
      </StyledReportsText>
    ),
  },
  {
    title: 'release',
    dataIndex: 'release_name',
  },
  {
    title: 'ingest_date',
    dataIndex: 'ingest_date',
    width: 125,
  },
  {
    title: 'receiver_id',
    dataIndex: 'receiver_id',
  },
  {
    title: 'platform',
    dataIndex: 'platform',
  },
  {
    title: 'joey_id',
    dataIndex: 'joey_id',
  },
  {
    title: 'joey_model',
    dataIndex: 'joey_model',
    width: 120,
  },
  {
    title: 'joey_software',
    dataIndex: 'joey_software',
    width: 140,
  },
  {
    title: 'hopper_model',
    dataIndex: 'hopper_model',
  },
  {
    title: 'hopper_software',
    dataIndex: 'hopper_software',
    width: 170,
  },
  {
    title: 'hopperp_id',
    dataIndex: 'hopperp_id',
  },
  {
    title: 'hopperp_model',
    dataIndex: 'hopperp_model',
    width: 160,
  },
  {
    title: 'hopperp_software',
    dataIndex: 'hopperp_software',
    width: 180,
  },
  {
    title: 'marked_log',
    dataIndex: 'marked_log',
    width: 150,
  },
  {
    title: 'has_attachment',
    dataIndex: 'has_attachment',
    width: 160,
    render: (_, { has_attachment }) => (has_attachment ? '✅' : '❌'),
  },
  {
    title: 'related_issue',
    dataIndex: 'related_issue',
  },
];

const Reports: FC<ReportsProps> = ({
  start_date,
  end_date,
  platform,
  release,
  device,
  className = '',
  componentRef,
  ...props
}) => {
  const [loading, setLoading] = useState(false);
  const [reports, setReports] = useState<BetaReportType[]>([]);
  const [tableParams, setTableParams] = useState<TableParams>({
    pagination: {
      current: 1,
      pageSize: DEFAULT_PAGE_SIZE,
      total: 0,
    },
  });
  const handleError = useHandleError();

  useImperativeHandle(
    componentRef,
    () => ({
      refetchData: async () => {
        await fetchData(true);
      },
    }),
    [],
  );

  const fetchData = async (isReset = false) => {
    try {
      setLoading(true);
      const { docs = [], totalDocs = 0 } = await getBetaReports({
        page: isReset ? 1 : (tableParams?.pagination?.current as number),
        limit: isReset
          ? DEFAULT_PAGE_SIZE
          : (tableParams?.pagination?.pageSize as number),
        start_date,
        end_date,
        platform,
        release,
        device,
      });
      setTableParams((prev) => ({
        ...prev,
        pagination: {
          ...prev.pagination,
          ...(isReset && {
            pageSize: DEFAULT_PAGE_SIZE,
            current: 1,
          }),
          total: totalDocs,
        },
      }));
      setReports(docs);
    } catch (e) {
      handleError(e);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    if (release !== undefined) {
      fetchData();
    }
  }, [
    tableParams?.pagination?.pageSize,
    tableParams?.pagination?.current,
    start_date,
    end_date,
    platform,
    release,
    device,
  ]);

  const handleTableChange: TableProps<BetaReportType>['onChange'] = (
    pagination,
    filters,
    sorter,
  ) => {
    setTableParams({
      pagination,
      filters,
      sortOrder: Array.isArray(sorter) ? undefined : sorter.order,
      sortField: Array.isArray(sorter) ? undefined : sorter.field,
    });
  };
  return (
    <Card title='Reports' className={`reports ${className}`} {...props}>
      <StyledReportsTable<BetaReportType>
        columns={columns}
        dataSource={reports}
        loading={loading}
        rowKey={(record) => record.id}
        pagination={tableParams.pagination}
        onChange={handleTableChange}
        scroll={{ x: 'max-content' }}
        sticky
      />
    </Card>
  );
};

export default Reports;
