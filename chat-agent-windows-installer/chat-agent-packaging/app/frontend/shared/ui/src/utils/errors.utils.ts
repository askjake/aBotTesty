import { FileValidationErrorType } from '@shared/ui/types/attachments.types';
import { NotificationInstance } from 'antd/lib/notification/interface';
import { ZodFormattedError } from 'zod';
import {
  GetServerSidePropsContext,
  GetServerSidePropsResult,
  PreviewData,
} from 'next';
import { TemplateErrorProps } from '@shared/ui/interfaces/templates.interfaces';
import { ParsedUrlQuery } from 'node:querystring';

export function formatFileCountError(error: FileValidationErrorType): string {
  if (!error.details) return error.message;

  const excess = error.details.current - error.details.maximum;
  const fileType =
    error.type === 'image_count'
      ? 'image'
      : error.type === 'document_count'
        ? 'document'
        : 'file';

  return [
    error.message,
    `Please remove ${excess} ${fileType}${excess > 1 ? 's' : ''}.`,
  ].join('\n');
}

export function formatFileSize(bytes: number): string {
  const mb = bytes / (1024 * 1024);
  return `${mb.toFixed(1)}MB`;
}

export const handleZodError = ({
  error,
  notification,
}: {
  error: ZodFormattedError<any>;
  notification: NotificationInstance;
}) => {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { _errors, ...fields } = error;
  Object.entries(fields).forEach(([key, value]) => {
    handleZodError({ error: value, notification });
    value?._errors.forEach((e: any) => {
      notification.error({
        title: `Validation error in the field "${key}"`,
        description: e,
      });
    });
  });
};

export const handleServerError = ({
  error,
  ctx,
}: {
  error: any;
  ctx?: GetServerSidePropsContext<ParsedUrlQuery, PreviewData>;
}): GetServerSidePropsResult<TemplateErrorProps> => {
  const status = error?.response?.status;

  const type = error?.response?.data?.type || 'Unknown error';
  const message =
    error?.response?.data?.detail ||
    error?.response?.data?.description ||
    error?.response?.data?.message ||
    'Something went wrong';

  console.error('[Server Error]', {
    timestamp: new Date().toISOString(),
    page: ctx?.resolvedUrl || 'Unknown page',
    method: ctx?.req?.method || 'Unknown method',
    errorType: error?.response ? 'Backend API Error' : 'Internal Server Error',
    status,
    statusText: error?.response?.statusText,
    type,
    message,
    // API details
    apiUrl: error?.config?.url,
    apiMethod: error?.config?.method?.toUpperCase(),
    // Request context
    userAgent: ctx?.req?.headers?.['user-agent'],
    referer: ctx?.req?.headers?.referer,
    // Full error details
    errorData: error?.response?.data,
    errorMessage: error?.message,
    stack: error?.stack,
    // Additional context for debugging
    ...(error?.response?.headers && {
      responseHeaders: error.response.headers,
    }),
  });

  if (status === 404) {
    return { notFound: true };
  }

  if (status === 403) {
    return {
      redirect: {
        destination: '/403',
        permanent: false,
      },
    };
  }

  return {
    redirect: {
      destination: `/500?type=${encodeURIComponent(type)}&message=${encodeURIComponent(message)}`,
      permanent: false,
    },
  };
};
