import {
  FC,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from 'react';
import { Attachments } from '@ant-design/x';
import { CloudUploadOutlined } from '@ant-design/icons';
import { App, GetProp, Upload } from 'antd';
import axios from 'axios';
import { z, ZodError } from 'zod';

import {
  ALLOWED_DOCUMENTS_MIME_TYPES,
  ALLOWED_FILES_MIME_TYPES_STRING,
  ALLOWED_IMAGES_MIME_TYPES,
  MAX_DOCUMENT_COUNT,
  MAX_IMAGE_COUNT,
} from '@shared/ui/constants/validation.constants';
import {
  checkAttachmentValidator,
  uploadAttachmentsValidator,
} from '@shared/ui/validators/attachments.validators';
import { calcTotalAttachments } from '@shared/ui/utils/attachments.utils';
import { formatFileCountError } from '@shared/ui/utils/errors.utils';
import useHandleError from '@shared/ui/hooks/useHandleError.hook';
import useDebouncedCallback from '@shared/ui/hooks/useDebounceCallback.hook';
import { useAppSelector } from '@shared/ui/store';
import { getAttachmentStatuses } from '@shared/ui/services/attachments.services';

import { StyledSenderHeaderBlockContainer } from '@shared/ui/components/molecules/Chat/SenderHeaderBlock/SenderHeaderBlock.styled';

import {
  FileType,
  FileValidationErrorType,
} from '@shared/ui/types/attachments.types';
import { AttachmentStatusEnum } from '@shared/ui/enums/chats.enums';
import { SenderHeaderBlockProps } from '@shared/ui/components/molecules/Chat/SenderHeaderBlock/SenderHeaderBlock.props';

const SenderHeaderBlock: FC<SenderHeaderBlockProps> = ({
  open = false,
  onOpenChange,
  onRemoveAttachment,
  onAddAttachment,
  setLoading,
  componentRef,
}) => {
  const { message, notification } = App.useApp();
  const [attachedFiles, setAttachedFiles] = useState<FileType[]>([]);
  const handleError = useHandleError();
  const aiTyping = useAppSelector((store) => store.chats.aiTyping);
  const totalDocuments = useMemo(
    () =>
      calcTotalAttachments({
        attachments: attachedFiles,
        types: ALLOWED_DOCUMENTS_MIME_TYPES,
      }),
    [attachedFiles],
  );
  const totalImages = useMemo(
    () =>
      calcTotalAttachments({
        attachments: attachedFiles,
        types: ALLOWED_IMAGES_MIME_TYPES,
      }),
    [attachedFiles],
  );
  const maxFilesCount = useMemo(
    () =>
      totalImages ? MAX_IMAGE_COUNT : totalDocuments ? MAX_DOCUMENT_COUNT : 1,
    [totalDocuments, totalImages],
  );
  const intervalRef = useRef<NodeJS.Timeout>(null);

  useImperativeHandle(
    componentRef,
    () => ({
      resetAttachments: () => {
        setAttachedFiles([]);
      },
    }),
    [],
  );

  const uploadFile = async (files: FileType[] = []) => {
    try {
      const { attachments: uploadedAttachments = [] } =
        await onAddAttachment(files);

      setAttachedFiles((prev) =>
        prev.map((item) => {
          const findFile = uploadedAttachments.find(
            ({ filename }) => filename === item.name,
          );
          if (findFile) {
            if (findFile?.error_message) {
              notification.error({
                title: 'Uploading error',
                description: `File "${findFile.filename}" didn't upload because of the error "${findFile?.error_message}"`,
              });
            }
            return {
              ...item,
              ...(findFile?.error_message && {
                status: 'error',
              }),
              attachment_id: findFile.attachment_id,
            };
          }
          return item;
        }),
      );
    } catch (error: any) {
      console.error(error);
      if (axios.isAxiosError(error) || error?.response) {
        setAttachedFiles((prev) =>
          prev.map((item) => ({
            ...item,
            status:
              files.findIndex(({ uid }) => item.uid === uid) !== -1
                ? 'error'
                : item.status,
          })),
        );
        const title = error?.response?.data?.type || 'Unknown error';
        const description =
          error?.response?.data?.description || 'Something went wrong';
        notification.error({
          title,
          description,
        });
      } else if (error instanceof ZodError) {
        const formatted: z.inferFormattedError<
          typeof uploadAttachmentsValidator
        > = error.format();
        const errorMessage = formatted.attachments?._errors[0];
        if (errorMessage) {
          const parsedError = JSON.parse(
            errorMessage,
          ) as FileValidationErrorType;
          if (
            ['total_count', 'image_count', 'document_count'].includes(
              parsedError.type,
            )
          ) {
            const formattedError = formatFileCountError(parsedError);
            setErrorsStatus({
              files,
              key: 'uid',
            });
            message.error(formattedError);
          } else if (parsedError.type === 'invalid_type') {
            const zodErrors = parsedError.details?.files || [];
            setErrorsStatus({
              files: files.filter(
                (item) =>
                  zodErrors.findIndex(({ name }) => item.name === name) !== -1,
              ),
              key: 'uid',
            });
            zodErrors.forEach((item) => {
              notification.error({
                title: `Validation error`,
                description: `The file "${item.name}" has invalid type`,
              });
            });
          } else if (parsedError.type === 'invalid_size') {
            const zodErrors = parsedError.details?.files || [];
            setErrorsStatus({
              files: files.filter(
                (item) =>
                  zodErrors.findIndex(({ name }) => item.name === name) !== -1,
              ),
              key: 'uid',
            });
            zodErrors.forEach((item) => {
              notification.error({
                message: `Validation error`,
                description: `The file "${item.name}" has invalid size`,
              });
            });
          } else {
            setErrorsStatus({
              files,
              key: 'uid',
            });
            notification.error({
              message: `Validation error`,
              description: parsedError.message,
            });
          }
        }
      } else {
        setErrorsStatus({
          files,
          key: 'uid',
        });
        notification.error({
          title: 'Unknown internal error',
          description: 'Something went wrong',
        });
      }
    }
  };

  const onDebouncedUploadingFiles = useDebouncedCallback(uploadFile, 500);

  useEffect(() => {
    const isEnableLoading = attachedFiles.some(
      (item) => item.status === 'uploading',
    );
    if (!aiTyping) {
      setLoading(isEnableLoading);
    }
  }, [attachedFiles, aiTyping]);

  useEffect(() => {
    const filteredUploadingFiles = attachedFiles.filter(
      (item) => item?.attachment_id && item.status === 'uploading',
    );
    const filteredInQueueFiles = attachedFiles.filter(
      (item) => !item?.attachment_id && item.status === 'uploading',
    );
    if (filteredUploadingFiles.length) {
      intervalRef.current = setInterval(async () => {
        try {
          const attachmentsStatuses = await getAttachmentStatuses(
            filteredUploadingFiles.map((item) => item.attachment_id as string),
          );
          setAttachedFiles((prev) =>
            prev.map((item) => {
              const currentAttachment = attachmentsStatuses
                ? attachmentsStatuses.status[item.attachment_id as string]
                : null;
              if (currentAttachment) {
                const status =
                  currentAttachment?.status === AttachmentStatusEnum.READY
                    ? 'done'
                    : currentAttachment?.status === AttachmentStatusEnum.FAILED
                      ? 'error'
                      : 'uploading';
                if (status === 'error' && item.status !== 'error') {
                  const description = currentAttachment?.message
                    ? currentAttachment?.message
                    : `The error occurred in uploading file "${item.name}"`;
                  notification.error({
                    title: `API error`,
                    description,
                  });
                  if (item?.attachment_id) {
                    onRemoveAttachment(item?.attachment_id as string);
                  }
                }

                const percent =
                  currentAttachment?.status === AttachmentStatusEnum.READY
                    ? 100
                    : currentAttachment?.progress;
                return {
                  ...item,
                  status,
                  percent,
                };
              }
              return item;
            }),
          );
        } catch (e) {
          handleError(e);
          setErrorsStatus({
            files: attachedFiles,
            key: 'uid',
          });
        }
      }, 1000);
    } else if (filteredInQueueFiles.length) {
      onDebouncedUploadingFiles(filteredInQueueFiles);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [attachedFiles]);

  const setErrorsStatus = ({
    files = [],
    key = 'uid',
  }: {
    files: FileType[];
    key: string;
  }) => {
    setAttachedFiles((prev) =>
      prev.map((file) => ({
        ...file,
        /* eslint-disable-next-line @typescript-eslint/ban-ts-comment */
        // @ts-expect-error
        ...(files.findIndex((item) => item[key] === file[key]) !== -1 && {
          status: 'error',
        }),
      })),
    );
  };

  const handleFileChange: GetProp<typeof Attachments, 'onChange'> = async (
    info,
  ) => {
    try {
      const isFileDelete =
        info.fileList.findIndex((item) => item.uid === info.file.uid) === -1 &&
        attachedFiles.findIndex((item) => item.uid === info.file.uid) !== -1;
      if (isFileDelete) {
        await handleRemove(info.file);
      } else {
        const checkIfExist =
          attachedFiles.findIndex((item) => item.uid === info.file.uid) !== -1;
        if (checkIfExist || info?.event) return;
        setAttachedFiles((prev) => [...prev, info.file]);
      }
    } catch (error: any) {
      handleError(error);
    }
  };

  const handleBeforeUploading = (file: FileType) => {
    const { error, success = false } = checkAttachmentValidator.safeParse({
      attachment: file,
    });
    if (!success) {
      const formattedError = error?.format();
      const errorMessage = formattedError?.attachment?._errors[0];
      if (errorMessage) {
        message.error(errorMessage);
      }
    }
    // Check duplicates
    const checkFileByName =
      attachedFiles.findIndex(({ name }) => name === file.name) !== -1;
    if (checkFileByName) {
      message.error(`File "${file.name}" is already uploaded`);
      return false;
    }
    return success || Upload.LIST_IGNORE;
  };

  const handleRemove = async (file: FileType) => {
    try {
      setAttachedFiles((prev) => prev.filter((item) => item.uid !== file.uid));
      if (file?.attachment_id) {
        onRemoveAttachment(file?.attachment_id);
      }
      return true;
    } catch (e) {
      handleError(e);
    }
  };

  return (
    <StyledSenderHeaderBlockContainer
      title='Attachments'
      open={open}
      onOpenChange={onOpenChange}
    >
      <Attachments
        accept={ALLOWED_FILES_MIME_TYPES_STRING}
        multiple
        maxCount={maxFilesCount}
        beforeUpload={handleBeforeUploading}
        items={attachedFiles}
        onChange={handleFileChange}
        placeholder={(type) =>
          type === 'drop'
            ? { title: 'Drop file here' }
            : {
                icon: <CloudUploadOutlined />,
                title: 'Upload files',
                description: `Click or drag files to this area to upload. Allowed to upload files only with "${Object.values({ ...ALLOWED_IMAGES_MIME_TYPES, ...ALLOWED_DOCUMENTS_MIME_TYPES }).join(',')}" types.`,
              }
        }
      />
    </StyledSenderHeaderBlockContainer>
  );
};

export default SenderHeaderBlock;
